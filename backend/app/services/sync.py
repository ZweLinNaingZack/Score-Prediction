"""Keeps the fixtures table in step with football-data.org while staying inside its rate limit."""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Fixture, PredictionRecord, StandingRow, Unlock
from app.leagues import COMPETITION_TO_LEAGUE_ID, LEAGUE_ID_TO_CODE
from app.services.football_data import get_live, get_matches_between, get_matches_by_ids, get_standings

log = logging.getLogger(__name__)

LIVE = {"IN_PLAY", "PAUSED"}
FINISHED = {"FINISHED", "AWARDED"}
UPCOMING = {"SCHEDULED", "TIMED"}
# POSTPONED, SUSPENDED and CANCELLED matches are not shown

MATCH_WINDOW = timedelta(hours=3)  # a match is "possibly live" this long after kickoff
UPCOMING_DAYS = 9  # the API allows at most 10 days per request
RETRY_AFTER_ERROR = 300  # seconds


def map_status(status: str) -> str | None:
    if status in LIVE:
        return "LIVE"
    if status in FINISHED:
        return "FINISHED"
    if status in UPCOMING:
        return "UPCOMING"
    return None


def short_code(name: str) -> str:
    letters = "".join(c for c in name if c.isalpha())
    return letters[:3].upper()


def _naive_utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)


def _team(team: dict) -> tuple[str, str]:
    name = team.get("shortName") or team.get("name") or "TBD"
    return name, team.get("tla") or short_code(name)


def to_values(item: dict) -> dict | None:
    """Turn one football-data.org match into column values, or None if it should not be stored."""
    league_id = COMPETITION_TO_LEAGUE_ID.get(item["competition"]["code"])
    status = map_status(item["status"])
    if league_id is None or status is None:
        return None
    home, home_short = _team(item["homeTeam"])
    away, away_short = _team(item["awayTeam"])
    full = (item.get("score") or {}).get("fullTime") or {}
    return {
        "id": item["id"],
        "league_id": league_id,
        "league": item["competition"]["name"],
        "home_team": home,
        "away_team": away,
        "home_short": home_short,
        "away_short": away_short,
        "home_crest": item["homeTeam"].get("crest"),
        "away_crest": item["awayTeam"].get("crest"),
        "kickoff": _naive_utc(item["utcDate"]),
        "status": status,
        "minute": item.get("minute") if status == "LIVE" else None,
        "home_goals": full.get("home"),
        "away_goals": full.get("away"),
    }


def upsert(db: Session, items: list[dict]) -> int:
    count = 0
    for item in items:
        values = to_values(item)
        if values is None:
            # a stored match that became postponed/cancelled must not linger as "upcoming"
            if item["status"] not in LIVE | FINISHED | UPCOMING and db.get(Fixture, item["id"]):
                db.execute(delete(PredictionRecord).where(PredictionRecord.fixture_id == item["id"]))
                db.execute(delete(Unlock).where(Unlock.fixture_id == item["id"]))
                db.execute(delete(Fixture).where(Fixture.id == item["id"]))
            continue
        row = db.get(Fixture, values["id"])
        if row is None:
            db.add(Fixture(**values))
        else:
            for key, val in values.items():
                setattr(row, key, val)
        count += 1
    db.commit()
    return count


async def refresh_upcoming(db: Session) -> int:
    today = datetime.now(timezone.utc).date()
    return upsert(
        db, await get_matches_between(today.isoformat(), (today + timedelta(days=UPCOMING_DAYS)).isoformat())
    )


async def refresh_by_ids(db: Session, ids: list[int]) -> int:
    total = 0
    for i in range(0, len(ids), 20):
        total += upsert(db, await get_matches_by_ids(ids[i : i + 20]))
    return total


async def refresh_live(db: Session) -> int:
    items = await get_live()
    total = upsert(db, items)
    # a match that dropped out of the live feed has ended: fetch its final state
    still_live = {i["id"] for i in items}
    gone = [f for f in db.scalars(select(Fixture.id).where(Fixture.status == "LIVE")) if f not in still_live]
    if gone:
        total += await refresh_by_ids(db, gone)
    return total


def live_window_open(db: Session, now: datetime | None = None) -> bool:
    """True when a stored match is live or could have started. Saves requests otherwise."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    row = db.scalar(
        select(Fixture.id)
        .where(
            (Fixture.status == "LIVE")
            | ((Fixture.status == "UPCOMING") & (Fixture.kickoff <= now) & (Fixture.kickoff > now - MATCH_WINDOW))
        )
        .limit(1)
    )
    return row is not None


_last: dict[str, float] = {"live": float("-inf"), "upcoming": float("-inf")}
_lock = asyncio.Lock()


async def _run(kind: str, ttl: int, fn, db: Session) -> None:
    now = time.monotonic()
    if now - _last[kind] < ttl:
        return
    try:
        await fn(db)
        _last[kind] = time.monotonic()
    except httpx.HTTPError as exc:
        log.warning("football-data.org %s refresh failed: %s", kind, exc)
        _last[kind] = time.monotonic() - ttl + RETRY_AFTER_ERROR  # serve stale data, retry later


async def refresh_if_stale(db: Session) -> None:
    """Called per request. Cheap when the cache is fresh; never raises on API errors."""
    if not settings.football_data_key:
        return
    async with _lock:
        await _run("upcoming", settings.upcoming_cache_seconds, refresh_upcoming, db)
        if live_window_open(db):
            await _run("live", settings.live_cache_seconds, refresh_live, db)


# ---- league tables ----
_standings_last: dict[int, float] = {}


async def refresh_standings(db: Session, league_id: int) -> int:
    """Replace the stored table of one league with the API's current one."""
    code = LEAGUE_ID_TO_CODE[league_id]
    tables = await get_standings(code)
    rows = []
    for t in tables:
        group = (t.get("group") or "").replace("_", " ").title() if len(tables) > 1 else ""
        for r in t.get("table", []):
            name, short = _team(r["team"])
            rows.append(
                StandingRow(
                    league_id=league_id, group=group, position=r["position"], team=name, short=short,
                    crest=r["team"].get("crest"), played=r["playedGames"], won=r["won"], draw=r["draw"],
                    lost=r["lost"], goals_for=r["goalsFor"], goals_against=r["goalsAgainst"], points=r["points"],
                )
            )
    if rows:  # never wipe a good table because the API sent nothing
        db.execute(delete(StandingRow).where(StandingRow.league_id == league_id))
        db.add_all(rows)
        db.commit()
    return len(rows)


async def refresh_standings_if_stale(db: Session, league_id: int) -> None:
    """Cheap when fresh; never raises on API errors (the stored table is served instead)."""
    if not settings.football_data_key or league_id not in LEAGUE_ID_TO_CODE:
        return
    async with _lock:
        has_rows = db.scalar(select(StandingRow.id).where(StandingRow.league_id == league_id).limit(1)) is not None
        age = time.monotonic() - _standings_last.get(league_id, float("-inf"))
        if has_rows and age < settings.standings_cache_seconds:
            return
        try:
            await refresh_standings(db, league_id)
            _standings_last[league_id] = time.monotonic()
        except httpx.HTTPError as exc:
            log.warning("football-data.org standings refresh failed for %s: %s", league_id, exc)
            _standings_last[league_id] = time.monotonic() - settings.standings_cache_seconds + RETRY_AFTER_ERROR
