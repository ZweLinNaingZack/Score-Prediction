"""API response shapes. Field names are camelCase on the wire to match frontend/lib/types.ts."""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ChancesOut(CamelModel):
    home: float  # 0..1
    draw: float
    away: float


class OddsOut(CamelModel):
    """Consensus of the bookmakers: average decimal odds and the chances they imply (margin removed)."""

    home: float
    draw: float
    away: float
    chances: ChancesOut
    bookmakers: int


class PredictionOut(CamelModel):
    model: str
    home: int
    away: int
    confidence: float
    reason: str | None = None
    chances: ChancesOut | None = None  # the model's own win/draw/away chances


class TeamOut(CamelModel):
    name: str
    short: str
    crest: str | None = None


class ScoreOut(CamelModel):
    home: int
    away: int


class MatchOut(CamelModel):
    id: int
    league_id: int
    status: str
    kickoff: str
    minute: int | None
    home: TeamOut
    away: TeamOut
    score: ScoreOut | None
    odds: OddsOut | None = None  # public market odds, when we have them
    unlocked: bool = False
    prediction_models: list[str] = []  # who has predicted; the predictions themselves need unlock
    predictions: list[PredictionOut]


class StandingOut(CamelModel):
    position: int
    team: str
    short: str
    crest: str | None = None
    played: int
    won: int
    draw: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    form: str  # last five results, oldest first, e.g. "WWDLW"


class StandingGroupOut(CamelModel):
    name: str | None = None  # None for a single table
    rows: list[StandingOut]


class StandingsOut(CamelModel):
    league_id: int
    groups: list[StandingGroupOut]


class LeaderboardOut(CamelModel):
    model: str
    played: int
    exact_scores: int
    correct_outcomes: int
