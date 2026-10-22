"""Builds the responses the frontend reads from the database."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Fixture, OddsRow, PredictionRecord, StandingRow, Unlock
from app.leagues import SOURCE_TO_MODEL
from app.schemas import (
    ChancesOut,
    OddsOut,
    LeaderboardOut,
    MatchOut,
    PredictionOut,
    ScoreOut,
    StandingGroupOut,
    StandingOut,
    StandingsOut,
    TeamOut,
)

FINISHED_VISIBLE_FOR = timedelta(days=3)


def _outcome(home: int, away: int) -> str:
    return "HOME" if home > away else "AWAY" if home < away else "DRAW"


def _latest_predictions(db: Session, fixture_ids: list[int]) -> dict[int, list[PredictionRecord]]:
    """Most recent prediction per (fixture, source)."""
    rows = db.scalars(
        select(PredictionRecord)
        .where(PredictionRecord.fixture_id.in_(fixture_ids))
        .order_by(PredictionRecord.created_at, PredictionRecord.id)
    )
    latest: dict[tuple[int, str], PredictionRecord] = {}
    for r in rows:
        latest[(r.fixture_id, r.source)] = r
    by_fixture: dict[int, list[PredictionRecord]] = defaultdict(list)
    for (fixture_id, _), r in latest.items():
        by_fixture[fixture_id].append(r)
    return by_fixture


def _odds_out(row: OddsRow | None) -> OddsOut | None:
    if row is None:
        return None
    return OddsOut(
        home=round(row.home_odds, 2), draw=round(row.draw_odds, 2), away=round(row.away_odds, 2),
        chances=ChancesOut(home=row.prob_home, draw=row.prob_draw, away=row.prob_away),
        bookmakers=row.bookmakers,
    )


def list_matches(db: Session, now: datetime | None = None, user_id: int | None = None) -> list[MatchOut]:
    """Predictions are only included for matches this user has unlocked."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    fixtures = db.scalars(
        select(Fixture)
        .where(
            (Fixture.status != "FINISHED") | (Fixture.kickoff >= now - FINISHED_VISIBLE_FOR)
        )
        .order_by(Fixture.kickoff)
    ).all()
    preds = _latest_predictions(db, [f.id for f in fixtures])
    odds = {o.fixture_id: o for o in db.scalars(select(OddsRow).where(OddsRow.fixture_id.in_([f.id for f in fixtures])))}
    unlocked: set[int] = set()
    if user_id is not None:
        unlocked = set(db.scalars(select(Unlock.fixture_id).where(Unlock.user_id == user_id)))

    out = []
    for f in fixtures:
        has_score = f.home_goals is not None and f.away_goals is not None
        out.append(
            MatchOut(
                id=f.id,
                league_id=f.league_id,
                status=f.status,
                kickoff=f.kickoff.isoformat() + "Z",
                minute=f.minute,
                home=TeamOut(name=f.home_team, short=f.home_short, crest=f.home_crest),
                away=TeamOut(name=f.away_team, short=f.away_short, crest=f.away_crest),
                score=ScoreOut(home=f.home_goals, away=f.away_goals) if has_score else None,
                odds=_odds_out(odds.get(f.id)),
                unlocked=f.id in unlocked,
                prediction_models=[SOURCE_TO_MODEL[p.source] for p in preds.get(f.id, []) if p.source in SOURCE_TO_MODEL],
                predictions=[
                    PredictionOut(
                        model=SOURCE_TO_MODEL[p.source],
                        home=p.home_goals,
                        away=p.away_goals,
                        confidence=p.confidence,
                        reason=p.reason,
                        chances=(
                            ChancesOut(home=p.prob_home, draw=p.prob_draw, away=p.prob_away)
                            if p.prob_home is not None and p.prob_draw is not None and p.prob_away is not None
                            else None
                        ),
                    )
                    for p in preds.get(f.id, [])
                    if p.source in SOURCE_TO_MODEL and f.id in unlocked
                ],
            )
        )
    return out


def leaderboard(db: Session) -> list[LeaderboardOut]:
    """Exact-score and correct-outcome counts over finished fixtures. Every model is listed."""
    stats = {m: {"played": 0, "exact": 0, "correct": 0} for m in SOURCE_TO_MODEL.values()}
    finished = {
        f.id: f
        for f in db.scalars(
            select(Fixture).where(
                Fixture.status == "FINISHED",
                Fixture.home_goals.is_not(None),
                Fixture.away_goals.is_not(None),
            )
        )
    }
    for fixture_id, preds in _latest_predictions(db, list(finished)).items():
        f = finished[fixture_id]
        actual = _outcome(f.home_goals, f.away_goals)
        for p in preds:
            model = SOURCE_TO_MODEL.get(p.source)
            if model is None:
                continue
            s = stats[model]
            s["played"] += 1
            s["exact"] += p.home_goals == f.home_goals and p.away_goals == f.away_goals
            s["correct"] += _outcome(p.home_goals, p.away_goals) == actual
    return [
        LeaderboardOut(model=m, played=s["played"], exact_scores=s["exact"], correct_outcomes=s["correct"])
        for m, s in stats.items()
    ]


def _form(db: Session, teams: set[str], last: int = 5) -> dict[str, str]:
    """Last results per team from stored finished matches, oldest first, e.g. 'WWDLW'."""
    results: dict[str, list[str]] = {t: [] for t in teams}
    rows = db.scalars(
        select(Fixture)
        .where(
            Fixture.status == "FINISHED",
            Fixture.home_goals.is_not(None),
            Fixture.away_goals.is_not(None),
            (Fixture.home_team.in_(teams)) | (Fixture.away_team.in_(teams)),
        )
        .order_by(Fixture.kickoff.desc())
    )
    for f in rows:
        for team, mine, theirs in ((f.home_team, f.home_goals, f.away_goals), (f.away_team, f.away_goals, f.home_goals)):
            if team in results and len(results[team]) < last:
                results[team].append("W" if mine > theirs else "L" if mine < theirs else "D")
    return {t: "".join(reversed(r)) for t, r in results.items()}


def standings(db: Session, league_id: int) -> StandingsOut:
    rows = db.scalars(
        select(StandingRow).where(StandingRow.league_id == league_id).order_by(StandingRow.group, StandingRow.position)
    ).all()
    form = _form(db, {r.team for r in rows})
    groups: dict[str, list[StandingOut]] = {}
    for r in rows:
        groups.setdefault(r.group, []).append(
            StandingOut(
                position=r.position, team=r.team, short=r.short, crest=r.crest, played=r.played, won=r.won,
                draw=r.draw, lost=r.lost, goals_for=r.goals_for, goals_against=r.goals_against,
                goal_difference=r.goals_for - r.goals_against, points=r.points, form=form.get(r.team, ""),
            )
        )
    return StandingsOut(
        league_id=league_id,
        groups=[StandingGroupOut(name=name or None, rows=table) for name, table in groups.items()],
    )
