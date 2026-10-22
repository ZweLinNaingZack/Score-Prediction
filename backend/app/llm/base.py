"""Shared prompt and output format for every predictor (your model and the LLMs)."""
from pydantic import BaseModel


class Prediction(BaseModel):
    outcome: str  # "HOME" | "DRAW" | "AWAY"
    home_goals: int
    away_goals: int
    confidence: float  # 0..1
    reason: str = ""  # one or two sentences on why, shown to users
    probs: dict[str, float] | None = None  # {"HOME": .., "DRAW": .., "AWAY": ..}, our model only


def build_prompt(home: str, away: str, league: str, date: str) -> str:
    return (
        f"Predict the football match {home} vs {away} ({league}, {date}). "
        'Reply ONLY with JSON: {"outcome": "HOME|DRAW|AWAY", "home_goals": int, '
        '"away_goals": int, "confidence": float between 0 and 1, '
        '"reason": "one or two short sentences explaining the pick"}'
    )
