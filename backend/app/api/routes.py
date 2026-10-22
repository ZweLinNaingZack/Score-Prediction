import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    hash_password,
    limiter,
    make_token,
    optional_user,
    password_problem,
    require_user,
    verify_password,
)
from app.db.database import get_db
from app.db.models import Fixture, Unlock, User
from app.leagues import LEAGUE_ID_TO_CODE
from app.schemas import LeaderboardOut, MatchOut, StandingsOut
from app.services import matches as matches_service
from app.services.sync import refresh_if_stale, refresh_standings_if_stale

router = APIRouter(prefix="/api")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class Register(Credentials):
    name: str = Field(max_length=100)


class AuthOut(BaseModel):
    token: str
    email: str
    name: str


def display_name(user: User) -> str:
    """The name to show: what they typed, or the part of the email before the @ for older accounts."""
    return user.name or user.email.split("@")[0]


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/auth/register", response_model=AuthOut, status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    name = " ".join(body.name.split())  # trim and collapse spaces
    if not 2 <= len(name) <= 40 or not name.isprintable():
        raise HTTPException(status_code=422, detail="Enter a name of 2 to 40 characters")
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    problem = password_problem(body.password)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    user = User(email=email, name=name, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That email already has an account")
    return AuthOut(token=make_token(user.id), email=user.email, name=display_name(user))


@router.post("/auth/login", response_model=AuthOut)
def login(body: Credentials, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    address = request.client.host if request.client else "unknown"
    wait = limiter.wait_seconds(address, email)
    if wait:  # locked: do not even check the password
        minutes = -(-wait // 60)
        unit = "minute" if minutes == 1 else "minutes"
        raise HTTPException(
            status_code=429,
            detail=f"Too many wrong attempts. Try again in {minutes} {unit}.",
            headers={"Retry-After": str(wait)},
        )
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(body.password, user.password_hash if user else None)
    if not user or not ok:
        limiter.record_failure(address, email)
        raise HTTPException(status_code=401, detail="Wrong email or password")
    limiter.record_success(address, email)
    return AuthOut(token=make_token(user.id), email=user.email, name=display_name(user))


@router.get("/auth/me")
def me(user: User = Depends(require_user)):
    return {"email": user.email, "name": display_name(user)}


@router.get("/matches", response_model=list[MatchOut])
async def matches(db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    await refresh_if_stale(db)
    return matches_service.list_matches(db, user_id=user.id if user else None)


@router.post("/matches/{match_id}/unlock")
def unlock(match_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Reveal this match's predictions to the signed-in user. Safe to call twice."""
    if db.get(Fixture, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    db.add(Unlock(user_id=user.id, fixture_id=match_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # already unlocked
    return {"unlocked": True}


@router.get("/standings/{league_id}", response_model=StandingsOut)
async def standings(league_id: int, db: Session = Depends(get_db)):
    if league_id not in LEAGUE_ID_TO_CODE:
        raise HTTPException(status_code=404, detail="No table for this league")
    await refresh_standings_if_stale(db, league_id)
    return matches_service.standings(db, league_id)


@router.get("/leaderboard", response_model=list[LeaderboardOut])
def leaderboard(db: Session = Depends(get_db)):
    return matches_service.leaderboard(db)
