"""Run before matches: refresh upcoming fixtures, then save a prediction from every AI provider
that has an API key and hasn't predicted that fixture yet.

    python -m scripts.fetch_and_predict

Predictions are made here rather than on web requests (visitors never call an AI), and only once per
match and source. Our own model is free, so it predicts every upcoming match. AI providers have
quotas, so they get the soonest matches first, spaced out, and stop for the run once a quota is hit.
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import settings
from app.db.database import SessionLocal, init_db
from app.db.models import Fixture, PredictionRecord
from app.llm.base import build_prompt
from app.llm.providers import PROVIDERS
from app.ml.model import PoissonModel
from app.services.sync import refresh_upcoming

HORIZON = timedelta(hours=settings.predict_hours_ahead)

KEYS = {
    "gpt": settings.openai_api_key,
    "grok": settings.xai_api_key,
    "gemini": settings.gemini_api_key,
    "claude": settings.anthropic_api_key,
}


def outcome(home: int, away: int) -> str:
    return "HOME" if home > away else "AWAY" if home < away else "DRAW"


async def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if settings.football_data_key:
            print(f"Fixtures refreshed: {await refresh_upcoming(db)}")
        else:
            print("FOOTBALL_DATA_KEY not set, using fixtures already in the database.")

        enabled = {name: fn for name, fn in PROVIDERS.items() if KEYS[name]}
        for name in PROVIDERS.keys() - enabled.keys():
            print(f"Skipping {name}: no API key set.")
        my_model = PoissonModel.load()
        if my_model is None:
            print("Skipping my_model: no trained model. Run: python -m app.ml.train")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        upcoming = db.scalars(
            select(Fixture)
            .where(Fixture.status == "UPCOMING", Fixture.kickoff > now)
            .order_by(Fixture.kickoff)
        ).all()

        saved = 0
        calls = 0  # AI requests this run
        stopped: set[str] = set()  # providers that hit their quota
        for f in upcoming:
            done = set(db.scalars(select(PredictionRecord.source).where(PredictionRecord.fixture_id == f.id)))
            if my_model is not None and "my_model" not in done:
                p = my_model.predict(f.home_team, f.away_team)  # None when a team is unknown
                if p is not None:
                    db.add(
                        PredictionRecord(
                            fixture_id=f.id,
                            source="my_model",
                            outcome=p.outcome,
                            home_goals=p.home_goals,
                            away_goals=p.away_goals,
                            confidence=p.confidence,
                            reason=p.reason,
                            prob_home=p.probs["HOME"] if p.probs else None,
                            prob_draw=p.probs["DRAW"] if p.probs else None,
                            prob_away=p.probs["AWAY"] if p.probs else None,
                        )
                    )
                    db.commit()
                    saved += 1
            if f.kickoff > now + HORIZON:
                continue  # AI predictions only for matches soon
            prompt = build_prompt(f.home_team, f.away_team, f.league, f.kickoff.date().isoformat())
            for name, fn in enabled.items():
                if name in done or name in stopped:
                    continue
                if calls >= settings.llm_max_per_run:
                    break
                if calls:
                    time.sleep(settings.llm_pause_seconds)  # stay under per-minute limits
                calls += 1
                try:
                    p = fn(prompt)
                except Exception as exc:  # one provider failing must not stop the rest
                    text = str(exc)
                    if "429" in text or "RESOURCE_EXHAUSTED" in text:
                        stopped.add(name)
                        print(f"  {name} quota reached, stopping it for this run. Run again later.")
                    else:
                        print(f"  {name} failed for {f.home_team} v {f.away_team}: {text[:200]}")
                    continue
                db.add(
                    PredictionRecord(
                        fixture_id=f.id,
                        source=name,
                        outcome=outcome(p.home_goals, p.away_goals),
                        home_goals=p.home_goals,
                        away_goals=p.away_goals,
                        confidence=min(max(p.confidence, 0.0), 1.0),
                        reason=p.reason.strip()[:600] or None,
                    )
                )
                db.commit()
                saved += 1
        print(f"Predictions saved: {saved} (AI requests: {calls})")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
