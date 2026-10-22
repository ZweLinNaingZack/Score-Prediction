"""Market odds from The Odds API (the-odds-api.com), shown next to our model's chances.

Only a script calls the API (scripts/update_odds.py) because the free plan has 500 credits a month and
one call costs one credit per league. We keep a consensus over all bookmakers it returns and never
show bookmaker names or links.
"""
import difflib
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Fixture, OddsRow
from app.leagues import LEAGUE_ID_TO_ODDS_KEY

BASE_URL = "https://api.the-odds-api.com/v4"
MATCH_WINDOW = timedelta(hours=3)  # kickoff times of the same match may differ a little between sources
LOOKAHEAD = timedelta(days=7)
MIN_NAME_SIMILARITY = 0.6


class OddsApiError(httpx.HTTPError):
    pass


async def _get(path: str, params: dict) -> tuple[list, str | None]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20) as client:
        resp = await client.get(path, params={**params, "apiKey": settings.odds_api_key})
    if resp.status_code >= 400:
        raise OddsApiError(f"{path} -> {resp.status_code}: {resp.text[:200]}")
    return resp.json(), resp.headers.get("x-requests-remaining")


async def get_sport_keys() -> set[str]:
    """Every sport key the API knows. This call does not use credits."""
    data, _ = await _get("/sports", {})
    return {s["key"] for s in data}


async def get_odds(sport_key: str) -> tuple[list[dict], str | None]:
    """Upcoming events with head-to-head (win/draw/win) decimal odds. Costs 1 credit."""
    return await _get(f"/sports/{sport_key}/odds", {"regions": "eu", "markets": "h2h", "oddsFormat": "decimal"})


# ---- consensus ----
def consensus(event: dict) -> dict | None:
    """Average odds and margin-free chances over bookmakers, or None if nobody quoted the match."""
    home, away = event["home_team"], event["away_team"]
    odds = [0.0, 0.0, 0.0]
    probs = [0.0, 0.0, 0.0]
    n = 0
    for bk in event.get("bookmakers", []):
        market = next((m for m in bk.get("markets", []) if m.get("key") == "h2h"), None)
        if not market:
            continue
        price = {o["name"]: o["price"] for o in market.get("outcomes", [])}
        if not all(k in price for k in (home, "Draw", away)):
            continue
        quote = [price[home], price["Draw"], price[away]]
        if min(quote) <= 1.0:
            continue
        inverse = [1.0 / q for q in quote]
        total = sum(inverse)  # above 1: the bookmaker's margin
        for i in range(3):
            odds[i] += quote[i]
            probs[i] += inverse[i] / total
        n += 1
    if n == 0:
        return None
    return {
        "home_odds": odds[0] / n, "draw_odds": odds[1] / n, "away_odds": odds[2] / n,
        "prob_home": probs[0] / n, "prob_draw": probs[1] / n, "prob_away": probs[2] / n,
        "bookmakers": n,
    }


# ---- matching our fixtures to their events ----
STOP = {"fc", "cf", "afc", "sc", "ac", "as", "ssc", "fk", "sk", "the", "and", "de", "of", "club", "fsv", "vfb",
        "vfl", "tsg", "rb", "us", "rc", "ud", "cd", "sv", "1", "calcio", "balompie"}
# our short names -> their fuller names (token by token)
ALIASES = {"man": "manchester", "utd": "united", "spurs": "tottenham", "wolves": "wolverhampton",
           "psg": "paris saint germain", "mgladbach": "monchengladbach", "inter": "internazionale",
           "atleti": "atletico", "barca": "barcelona", "hsv": "hamburger", "rennais": "rennes"}


def tokens(name: str) -> set[str]:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    text = text.replace("&", " and ").replace("'", "")
    out: set[str] = set()
    for word in re.findall(r"[a-z0-9]+", text):
        for t in ALIASES.get(word, word).split():
            if t not in STOP:
                out.add(t)
    return out


def _same_token(x: str, y: str) -> bool:
    return x == y or difflib.SequenceMatcher(None, x, y).ratio() >= 0.85  # tolerates small spelling gaps


def similarity(a: str, b: str) -> float:
    """Share of the shorter name's words that appear in the other (0..1)."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    small, large = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    hits = sum(any(_same_token(x, y) for y in large) for x in small)
    return hits / len(small)


def _event_time(event: dict) -> datetime:
    return datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)


def match_event(fixture: Fixture, events: list[dict]) -> dict | None:
    """The event with a close kickoff and similar team names (home and away in the same order)."""
    best, best_score = None, 0.0
    for e in events:
        if abs(_event_time(e) - fixture.kickoff) > MATCH_WINDOW:
            continue
        s_home = similarity(fixture.home_team, e["home_team"])
        s_away = similarity(fixture.away_team, e["away_team"])
        if min(s_home, s_away) >= MIN_NAME_SIMILARITY and s_home + s_away > best_score:
            best, best_score = e, s_home + s_away
    return best


# ---- refresh ----
async def refresh_odds(db: Session, now: datetime | None = None) -> dict:
    """Fetch odds for leagues that have matches in the next week and store the consensus.
    Returns {"saved": n, "unmatched": [..], "skipped": [..], "remaining": credits left or None}."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    summary: dict = {"saved": 0, "unmatched": [], "skipped": [], "remaining": None}
    for league_id, key in LEAGUE_ID_TO_ODDS_KEY.items():
        fixtures = db.scalars(
            select(Fixture).where(
                Fixture.league_id == league_id, Fixture.status == "UPCOMING",
                Fixture.kickoff > now, Fixture.kickoff <= now + LOOKAHEAD,
            )
        ).all()
        if not fixtures:
            summary["skipped"].append(key)  # saves a credit
            continue
        events, remaining = await get_odds(key)
        summary["remaining"] = remaining
        for f in fixtures:
            event = match_event(f, events)
            values = consensus(event) if event else None
            if values is None:
                summary["unmatched"].append(f"{f.home_team} v {f.away_team}")
                continue
            row = db.get(OddsRow, f.id)
            if row is None:
                db.add(OddsRow(fixture_id=f.id, updated_at=datetime.now(timezone.utc), **values))
            else:
                for k, v in values.items():
                    setattr(row, k, v)
                row.updated_at = datetime.now(timezone.utc)
            summary["saved"] += 1
        db.commit()
    return summary
