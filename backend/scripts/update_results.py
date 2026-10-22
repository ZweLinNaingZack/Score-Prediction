"""Run after matches: fetch final scores for fixtures that should be over.

    python -m scripts.update_results
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import settings
from app.db.database import SessionLocal, init_db
from app.db.models import Fixture
from app.services.sync import refresh_by_ids


async def main() -> None:
    if not settings.football_data_key:
        print("FOOTBALL_DATA_KEY not set.")
        return
    init_db()
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        ids = list(
            db.scalars(select(Fixture.id).where(Fixture.status != "FINISHED", Fixture.kickoff < cutoff))
        )
        print(f"Checking {len(ids)} fixtures")
        if ids:
            print(f"Updated: {await refresh_by_ids(db, ids)}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
