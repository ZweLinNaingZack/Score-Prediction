"""Fetch market odds for upcoming matches and store a consensus for the comparison card.

    python -m scripts.update_odds

Needs ODDS_API_KEY in .env (free key: the-odds-api.com, 500 credits a month). Costs 1 credit per league
that has matches in the next 7 days, so twice a day is about 360 credits a month for six leagues.
"""
import asyncio

from app.config import settings
from app.db.database import SessionLocal, init_db
from app.leagues import LEAGUE_ID_TO_ODDS_KEY
from app.services.odds import get_sport_keys, refresh_odds


async def main() -> None:
    if not settings.odds_api_key:
        print("ODDS_API_KEY not set. Get a free key at https://the-odds-api.com and add it to backend/.env")
        return
    known = await get_sport_keys()  # free call: catches a wrong sport key before it wastes credits
    for key in LEAGUE_ID_TO_ODDS_KEY.values():
        if key not in known:
            print(f"Warning: sport key {key} is not offered by the API right now.")
    init_db()
    db = SessionLocal()
    try:
        s = await refresh_odds(db)
    finally:
        db.close()
    print(f"Odds saved for {s['saved']} matches. Credits left: {s['remaining']}")
    if s["skipped"]:
        print("No upcoming matches (no credit used):", ", ".join(s["skipped"]))
    if s["unmatched"]:
        print(f"No odds found for {len(s['unmatched'])} matches (too far ahead, or names did not match):")
        for m in s["unmatched"][:15]:
            print("  ", m)


if __name__ == "__main__":
    asyncio.run(main())
