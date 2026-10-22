"""Accounts and login tokens, standard library only (Python 3.15 lacks some wheels).

Passwords: scrypt with a random salt. Tokens: base64(payload) + "." + HMAC-SHA256 signature,
valid for TOKEN_DAYS. The signing secret is AUTH_SECRET, or a random one kept in data/.auth_secret.
"""
import base64
import hashlib
import hmac
import json
import math
import secrets
import time
from pathlib import Path

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.db.models import User

TOKEN_DAYS = 30
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
_SECRET_FILE = Path(__file__).resolve().parents[1] / "data" / ".auth_secret"
_secret_cache: bytes | None = None


def _secret() -> bytes:
    global _secret_cache
    if _secret_cache is None:
        if settings.auth_secret:
            _secret_cache = settings.auth_secret.encode()
        else:
            if not _SECRET_FILE.exists():
                _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
                _SECRET_FILE.write_text(secrets.token_hex(32))
            _secret_cache = _SECRET_FILE.read_text().strip().encode()
    return _secret_cache


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Always does one scrypt run, even for an unknown user, so timing does not reveal who exists."""
    try:
        _, n, r, p, salt, digest = (stored or "").split("$")
        expected = bytes.fromhex(digest)
        salt_bytes = bytes.fromhex(salt)
        params = (int(n), int(r), int(p))
    except ValueError:
        expected, salt_bytes, params = b"\0" * 64, b"\0" * 16, (SCRYPT_N, SCRYPT_R, SCRYPT_P)
        stored = None
    got = hashlib.scrypt(password.encode(), salt=salt_bytes, n=params[0], r=params[1], p=params[2], dklen=len(expected))
    return stored is not None and hmac.compare_digest(got, expected)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(user_id: int, now: float | None = None) -> str:
    payload = _b64(json.dumps({"sub": user_id, "exp": int((now or time.time()) + TOKEN_DAYS * 86400)}).encode())
    sig = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(token: str, now: float | None = None) -> int | None:
    """User id from a valid, unexpired token, else None."""
    try:
        payload, sig = token.split(".")
        good = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        data = json.loads(_unb64(payload))
        if data["exp"] < (now or time.time()):
            return None
        return int(data["sub"])
    except (ValueError, KeyError, TypeError):
        return None


def optional_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    user_id = read_token(authorization[7:].strip())
    return db.get(User, user_id) if user_id is not None else None


def require_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


# ---- password rules ----
def password_problem(password: str) -> str | None:
    """Why a new password is too weak, or None if it is fine."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not any(c.islower() for c in password):
        return "Password needs a lowercase letter"
    if not any(c.isupper() for c in password):
        return "Password needs a capital letter"
    if not any(c.isdigit() for c in password):
        return "Password needs a number"
    if all(c.isalnum() for c in password):
        return "Password needs a symbol, like ! or #"
    return None


# ---- login rate limit ----
MAX_FAILS = 5  # wrong tries allowed per email+address
LOCK_SECONDS = 300  # then wait this long
MAX_FAILS_PER_ADDRESS = 20  # wrong tries across all emails from one address


def _now() -> float:
    return time.monotonic()


class LoginLimiter:
    """Counts wrong logins in memory. Resets if the server restarts and is per server process;
    use a shared store (database or Redis) if the API ever runs as several processes."""

    def __init__(self) -> None:
        self._fails: dict[str, tuple[int, float]] = {}  # key -> (count, window or lock expiry)

    def reset(self) -> None:
        self._fails.clear()

    def _purge(self) -> None:
        now = _now()
        for key in [k for k, (_, until) in self._fails.items() if until <= now]:
            del self._fails[key]

    @staticmethod
    def _keys(address: str, email: str) -> tuple[tuple[str, int], tuple[str, int]]:
        return (f"{address}|{email}", MAX_FAILS), (f"{address}|*", MAX_FAILS_PER_ADDRESS)

    def wait_seconds(self, address: str, email: str) -> int:
        """Seconds left on a lock, 0 if this attempt may go ahead."""
        self._purge()
        now = _now()
        left = 0.0
        for key, limit in self._keys(address, email):
            count, until = self._fails.get(key, (0, 0.0))
            if count >= limit:
                left = max(left, until - now)
        return math.ceil(left) if left > 0 else 0

    def record_failure(self, address: str, email: str) -> None:
        now = _now()
        # The count lives LOCK_SECONDS after the latest wrong try. Reaching the limit locks the key
        # for that long, and nothing is counted while locked (the route refuses first).
        for key, _ in self._keys(address, email):
            count, _until = self._fails.get(key, (0, 0.0))
            self._fails[key] = (count + 1, now + LOCK_SECONDS)

    def record_success(self, address: str, email: str) -> None:
        self._fails.pop(f"{address}|{email}", None)


limiter = LoginLimiter()
