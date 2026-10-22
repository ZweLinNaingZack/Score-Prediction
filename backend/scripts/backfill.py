"""Load finished matches from past seasons so the ML model has data to learn from.

    python -m scripts.backfill            # last season and this one
    python -m scripts.backfill 2024 2025  # chosen seasons (the year the season starts)

One request per league and season. The free tier allows 10 per minute, so this pauses between
calls. Seasons your plan cannot read are reported and skipped.
"""
import asyncio
import sys
from datetime import datetime, timezone

from app.config import settings
from app.db.database import SessionLocal, init_db
from app.leagues import COMPETITION_CODES
from app.services.football_data import get_competition_matches
from app.services.sync import upsert

PAUSE_SECONDS = 7


def current_season() -> int:
    now = datetime.now(timezone.utc)
    return now.year if now.month >= 8 else now.year - 1


async def main(seasons: list[int]) -> None:
    if not settings.football_data_key:
        print("FOOTBALL_DATA_KEY not set.")
        return
    init_db()
    db = SessionLocal()
    try:
        for season in seasons:
            for code in COMPETITION_CODES:
                try:
                    items = await get_competition_matches(code, season)
                except Exception as exc:  # one league/season failing must not stop the rest
                    print(f"{code} {season}: skipped ({exc})")
                else:
                    print(f"{code} {season}: stored {upsert(db, items)}")
                await asyncio.sleep(PAUSE_SECONDS)
    finally:
        db.close()


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]]
    asyncio.run(main(args or [current_season() - 1, current_season()]))
