"""Client for football-data.org (v4). Free tier: 10 requests/minute, a fixed set of competitions."""
import httpx

from app.config import settings
from app.leagues import COMPETITION_CODES

BASE_URL = "https://api.football-data.org/v4"
CODES = ",".join(COMPETITION_CODES)


class FootballDataError(httpx.HTTPError):
    """Bad key, restricted competition or rate limit. The body's `message` explains which."""


async def _get(path: str, params: dict) -> dict:
    headers = {"X-Auth-Token": settings.football_data_key}
    async with httpx.AsyncClient(base_url=BASE_URL, headers=headers, timeout=20) as client:
        resp = await client.get(path, params=params)
        if resp.status_code >= 400:
            try:
                message = resp.json().get("message", resp.text)
            except ValueError:
                message = resp.text
            raise FootballDataError(f"{path} {params} -> {resp.status_code}: {message}")
        return resp.json()


async def get_matches_between(start: str, end: str) -> list[dict]:
    """Matches in a date range (YYYY-MM-DD). The API allows at most 10 days per request."""
    data = await _get("/matches", {"competitions": CODES, "dateFrom": start, "dateTo": end})
    return data.get("matches", [])


async def get_live() -> list[dict]:
    data = await _get("/matches", {"competitions": CODES, "status": "IN_PLAY,PAUSED"})
    return data.get("matches", [])


async def get_competition_matches(code: str, season: int) -> list[dict]:
    """All finished matches of one competition season (used to backfill history for training)."""
    data = await _get(f"/competitions/{code}/matches", {"season": season, "status": "FINISHED"})
    return data.get("matches", [])


async def get_matches_by_ids(match_ids: list[int]) -> list[dict]:
    data = await _get("/matches", {"ids": ",".join(str(i) for i in match_ids)})
    return data.get("matches", [])


async def get_standings(code: str) -> list[dict]:
    """League table(s) of one competition. Each item has a `table` list; TOTAL excludes home/away splits."""
    data = await _get(f"/competitions/{code}/standings", {})
    return [s for s in data.get("standings", []) if s.get("type", "TOTAL") == "TOTAL"]
