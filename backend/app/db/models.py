from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Fixture(Base):
    __tablename__ = "fixtures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # football-data.org match id
    league_id: Mapped[int] = mapped_column(Integer, index=True)  # frontend league id (see app/leagues.py)
    league: Mapped[str] = mapped_column(String)
    home_team: Mapped[str] = mapped_column(String)
    away_team: Mapped[str] = mapped_column(String)
    home_short: Mapped[str] = mapped_column(String)
    away_short: Mapped[str] = mapped_column(String)
    home_crest: Mapped[str | None] = mapped_column(String, nullable=True)  # logo URL
    away_crest: Mapped[str | None] = mapped_column(String, nullable=True)
    kickoff: Mapped[datetime] = mapped_column(DateTime)  # naive UTC
    status: Mapped[str] = mapped_column(String, default="UPCOMING", index=True)  # LIVE | UPCOMING | FINISHED
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PredictionRecord(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"))
    source: Mapped[str] = mapped_column(String)  # "my_model", "gpt", "grok", "gemini", "claude"
    outcome: Mapped[str] = mapped_column(String)
    home_goals: Mapped[int] = mapped_column(Integer)
    away_goals: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)  # why, shown to users
    prob_home: Mapped[float | None] = mapped_column(Float, nullable=True)  # model chances, for the market comparison
    prob_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    prob_away: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String, nullable=True)  # display name; older accounts have none
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Unlock(Base):
    """A user has unlocked the predictions of one match."""

    __tablename__ = "unlocks"
    __table_args__ = (UniqueConstraint("user_id", "fixture_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class StandingRow(Base):
    """One line of a league table, replaced wholesale on every refresh."""

    __tablename__ = "standings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    group: Mapped[str] = mapped_column(String, default="")  # "" for a single table
    position: Mapped[int] = mapped_column(Integer)
    team: Mapped[str] = mapped_column(String)
    short: Mapped[str] = mapped_column(String)
    crest: Mapped[str | None] = mapped_column(String, nullable=True)
    played: Mapped[int] = mapped_column(Integer)
    won: Mapped[int] = mapped_column(Integer)
    draw: Mapped[int] = mapped_column(Integer)
    lost: Mapped[int] = mapped_column(Integer)
    goals_for: Mapped[int] = mapped_column(Integer)
    goals_against: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)


class OddsRow(Base):
    """Consensus market odds for one fixture, averaged over the bookmakers The Odds API returns."""

    __tablename__ = "odds"
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), primary_key=True)
    home_odds: Mapped[float] = mapped_column(Float)  # average decimal odds
    draw_odds: Mapped[float] = mapped_column(Float)
    away_odds: Mapped[float] = mapped_column(Float)
    prob_home: Mapped[float] = mapped_column(Float)  # chances with the bookmakers' margin removed
    prob_draw: Mapped[float] = mapped_column(Float)
    prob_away: Mapped[float] = mapped_column(Float)
    bookmakers: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
