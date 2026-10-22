"""Fit the model on finished fixtures in the database and save it to data/model.json.

    python -m app.ml.tune     # optional, finds the best settings (slow, a few minutes)
    python -m app.ml.train

Fill the database with history first: python -m scripts.backfill 2022 2023 2024 2025 2026
"""
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.database import SessionLocal, init_db
from app.db.models import Fixture
from app.ml.model import MODEL_PATH, Game, PoissonModel, day_number, load_params

MIN_GAMES_TO_TRAIN = 100
SETTINGS = ("half_life_days", "prior", "use_dc", "draw_boost", "home_prior")


def _outcome(h: int, a: int) -> str:
    return "HOME" if h > a else "AWAY" if h < a else "DRAW"


def load_games(db) -> list[Game]:
    rows = db.scalars(
        select(Fixture)
        .where(Fixture.status == "FINISHED", Fixture.home_goals.is_not(None), Fixture.away_goals.is_not(None))
        .order_by(Fixture.kickoff)
    )
    return [
        Game(f.home_team, f.away_team, f.home_goals, f.away_goals, day_number(f.kickoff.replace(tzinfo=timezone.utc)))
        for f in rows
    ]


def evaluate(games: list[Game], settings: dict) -> None:
    """Fit on the older 80%, score on the newest 20% (one fit; app.ml.tune does the thorough test)."""
    cut = int(len(games) * 0.8)
    model = PoissonModel.fit(games[:cut], as_of=games[cut].day, **settings)
    tested = outcome_hits = exact_hits = home_wins = 0
    for g in games[cut:]:
        p = model.predict(g.home, g.away)
        if p is None:
            continue
        tested += 1
        actual = _outcome(g.home_goals, g.away_goals)
        outcome_hits += p.outcome == actual
        exact_hits += (p.home_goals, p.away_goals) == (g.home_goals, g.away_goals)
        home_wins += actual == "HOME"
    if not tested:
        print("Hold-out: no testable games.")
        return
    print(
        f"Hold-out ({tested} games): outcome {outcome_hits / tested:.1%}, exact score {exact_hits / tested:.1%}"
        f"  (always-home baseline {home_wins / tested:.1%})"
    )


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        games = load_games(db)
    finally:
        db.close()
    games.sort(key=lambda g: g.day)
    print(f"Finished games in database: {len(games)}")
    if len(games) < MIN_GAMES_TO_TRAIN:
        print(f"Need at least {MIN_GAMES_TO_TRAIN}. Run: python -m scripts.backfill")
        return
    params = load_params()
    settings = {k: params[k] for k in SETTINGS}
    print(f"Settings: {settings}")
    evaluate(games, settings)
    model = PoissonModel.fit(games, as_of=day_number(datetime.now(timezone.utc)), **settings)
    model.save()
    print(f"Saved model for {len(model.attack)} teams (rho={model.rho:+.2f}) to {MODEL_PATH}")


if __name__ == "__main__":
    main()
