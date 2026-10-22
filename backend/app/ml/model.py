"""Our own predictor: a Dixon-Coles style Poisson model, pure Python (no numpy needed).

Each team gets an attack and a defence strength. Expected goals are

    home = avg_home_goals * attack[home] * defence[away]
    away = avg_away_goals * attack[away] * defence[home]

Strengths are fitted from finished matches by iterating to the maximum-likelihood answer. Three
things make it more accurate than a plain Poisson model:

  * time decay: a match played a half-life ago counts half as much as one played today
  * shrinkage: teams with few games are pulled toward average, so a hot streak is not trusted
  * a per-team home advantage: some grounds are worth more than others (shrunk toward the average)
  * the Dixon-Coles correction (rho): football has more 0-0 and 1-1 results and fewer 1-0 / 0-1
    results than two independent Poisson counts predict. rho is fitted from the data.

Optionally `draw_boost` nudges draw chances up. Football is very random, so even the best model
only reaches about 50-55% on win/draw/loss.
"""
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.llm.base import Prediction

MODEL_PATH = Path(__file__).resolve().parents[2] / "data" / "model.json"
PARAMS_PATH = Path(__file__).resolve().parents[2] / "data" / "params.json"  # written by app.ml.tune
MAX_GOALS = 8
MIN_GAMES = 3  # a team needs this many games in training to be predicted

# Used when tune has not been run
DEFAULT_PARAMS = {"half_life_days": 365.0, "prior": 4.0, "use_dc": False, "draw_boost": 0.0, "home_prior": 10.0}


@dataclass
class Game:
    home: str
    away: str
    home_goals: int
    away_goals: int
    day: float = 0.0  # days since 1970-01-01 when it was played


def day_number(when: datetime) -> float:
    return when.timestamp() / 86400.0


def load_params() -> dict:
    params = dict(DEFAULT_PARAMS)
    if PARAMS_PATH.exists():
        params.update(json.loads(PARAMS_PATH.read_text()))
    return params


def _poisson(lam: float) -> list[float]:
    p = [math.exp(-lam)]
    for k in range(1, MAX_GOALS + 1):
        p.append(p[-1] * lam / k)
    return p


def _tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    """Dixon-Coles adjustment for the four lowest scorelines."""
    if x == 0 and y == 0:
        return 1.0 - lam * mu * rho
    if x == 0 and y == 1:
        return 1.0 + lam * rho
    if x == 1 and y == 0:
        return 1.0 + mu * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def _outcome(i: int, j: int) -> str:
    return "HOME" if i > j else "AWAY" if i < j else "DRAW"


def _vs_avg(ratio: float) -> str:
    """1.24 -> '24% above', 0.9 -> '10% below'."""
    pct = round(abs(ratio - 1) * 100)
    return f"{pct}% above" if ratio >= 1 else f"{pct}% below"


class PoissonModel:
    def __init__(
        self,
        mu_home: float,
        mu_away: float,
        attack: dict,
        defence: dict,
        games: dict,
        rho: float = 0.0,
        draw_boost: float = 0.0,
        trained_on: int = 0,
        home_adv: dict | None = None,
    ):
        self.mu_home, self.mu_away = mu_home, mu_away
        self.attack, self.defence, self.games = attack, defence, games
        self.rho, self.draw_boost, self.trained_on = rho, draw_boost, trained_on
        self.home_adv = home_adv or {}  # team -> multiplier on its home goals, 1.0 = average

    # ---- training ----
    @classmethod
    def fit(
        cls,
        games: list[Game],
        as_of: float | None = None,
        half_life_days: float = 365.0,
        prior: float = 3.0,
        use_dc: bool = True,
        draw_boost: float = 0.0,
        home_prior: float | None = 10.0,
        rounds: int = 60,
    ):
        """`as_of` is the day (see day_number) the model is for: older matches weigh less."""
        if not games:
            raise ValueError("no games to fit")
        as_of = max(g.day for g in games) if as_of is None else as_of
        w = [0.5 ** (max(as_of - g.day, 0.0) / half_life_days) for g in games]
        total = sum(w)
        mu_h = sum(wi * g.home_goals for wi, g in zip(w, games)) / total
        mu_a = sum(wi * g.away_goals for wi, g in zip(w, games)) / total

        teams = {t for g in games for t in (g.home, g.away)}
        att = {t: 1.0 for t in teams}
        dfn = {t: 1.0 for t in teams}
        count = {t: 0 for t in teams}
        for g in games:
            count[g.home] += 1
            count[g.away] += 1

        for _ in range(rounds):
            a_num = dict.fromkeys(teams, prior)
            a_den = dict.fromkeys(teams, prior)
            d_num = dict.fromkeys(teams, prior)
            d_den = dict.fromkeys(teams, prior)
            for wi, g in zip(w, games):
                a_num[g.home] += wi * g.home_goals
                a_den[g.home] += wi * mu_h * dfn[g.away]
                a_num[g.away] += wi * g.away_goals
                a_den[g.away] += wi * mu_a * dfn[g.home]
                d_num[g.away] += wi * g.home_goals  # goals the away side's defence let in
                d_den[g.away] += wi * mu_h * att[g.home]
                d_num[g.home] += wi * g.away_goals
                d_den[g.home] += wi * mu_a * att[g.away]
            att = {t: a_num[t] / a_den[t] for t in teams}
            dfn = {t: d_num[t] / d_den[t] for t in teams}
            # keep the average at 1 so the scale stays pinned to mu_h / mu_a
            a_mean = sum(att.values()) / len(att)
            d_mean = sum(dfn.values()) / len(dfn)
            att = {t: v / a_mean for t, v in att.items()}
            dfn = {t: v / d_mean for t, v in dfn.items()}

        rho = cls._fit_rho(games, w, mu_h, mu_a, att, dfn) if use_dc else 0.0
        model = cls(mu_h, mu_a, att, dfn, count, rho, draw_boost, len(games))
        if home_prior is not None:
            model.fit_home_advantage(games, as_of, half_life_days, home_prior)
        return model

    def fit_home_advantage(self, games: list[Game], as_of: float, half_life_days: float, prior: float = 10.0) -> None:
        """Per team: its (time-weighted) home goals divided by what the ratings expected at home.
        `prior` pseudo-goals of exactly-average pull small samples toward 1.0."""
        self.home_adv = {}
        num: dict[str, float] = {}
        den: dict[str, float] = {}
        for g in games:
            w = 0.5 ** (max(as_of - g.day, 0.0) / half_life_days)
            expected = self.mu_home * self.attack[g.home] * self.defence[g.away]
            num[g.home] = num.get(g.home, 0.0) + w * g.home_goals
            den[g.home] = den.get(g.home, 0.0) + w * expected
        self.home_adv = {t: (num[t] + prior) / (den[t] + prior) for t in num}
    @staticmethod
    def _fit_rho(games, w, mu_h, mu_a, att, dfn) -> float:
        """Maximum-likelihood rho on a grid. Only the four low scorelines depend on it."""
        low = [
            (wi, g.home_goals, g.away_goals, mu_h * att[g.home] * dfn[g.away], mu_a * att[g.away] * dfn[g.home])
            for wi, g in zip(w, games)
            if g.home_goals <= 1 and g.away_goals <= 1
        ]
        best, best_ll = 0.0, -math.inf
        for step in range(-30, 11):
            rho = step / 100
            ll = 0.0
            for wi, x, y, lam, mu in low:
                t = _tau(x, y, lam, mu, rho)
                if t <= 0:
                    ll = -math.inf
                    break
                ll += wi * math.log(t)
            if ll > best_ll:
                best, best_ll = rho, ll
        return best

    # ---- prediction ----
    def knows(self, team: str) -> bool:
        return self.games.get(team, 0) >= MIN_GAMES

    def expected_goals(self, home: str, away: str) -> tuple[float, float]:
        lam_h = self.mu_home * self.attack[home] * self.defence[away] * self.home_adv.get(home, 1.0)
        lam_a = self.mu_away * self.attack[away] * self.defence[home]
        return lam_h, lam_a

    def grid(self, home: str, away: str) -> list[list[float]]:
        """P(home scores i, away scores j), adjusted for low scores and draws, summing to 1."""
        lam, mu = self.expected_goals(home, away)
        ph, pa = _poisson(lam), _poisson(mu)
        cells = [[ph[i] * pa[j] * _tau(i, j, lam, mu, self.rho) for j in range(MAX_GOALS + 1)] for i in range(MAX_GOALS + 1)]
        if self.draw_boost:
            for i in range(MAX_GOALS + 1):
                cells[i][i] *= 1.0 + self.draw_boost
        total = sum(map(sum, cells))
        return [[c / total for c in row] for row in cells]

    def outcome_probs(self, home: str, away: str) -> dict[str, float]:
        grid = self.grid(home, away)
        probs = {"HOME": 0.0, "DRAW": 0.0, "AWAY": 0.0}
        for i, row in enumerate(grid):
            for j, p in enumerate(row):
                probs[_outcome(i, j)] += p
        return probs

    def predict(self, home: str, away: str) -> Prediction | None:
        """Most likely outcome, then the most likely scoreline within it. None if a team is unknown."""
        if not (self.knows(home) and self.knows(away)):
            return None
        grid = self.grid(home, away)
        probs = {"HOME": 0.0, "DRAW": 0.0, "AWAY": 0.0}
        for i, row in enumerate(grid):
            for j, p in enumerate(row):
                probs[_outcome(i, j)] += p
        outcome = max(probs, key=probs.get)
        _, i, j = max(
            (grid[i][j], i, j)
            for i in range(MAX_GOALS + 1)
            for j in range(MAX_GOALS + 1)
            if _outcome(i, j) == outcome
        )
        lam_h, lam_a = self.expected_goals(home, away)
        return Prediction(
            outcome=outcome,
            home_goals=i,
            away_goals=j,
            confidence=round(probs[outcome], 3),
            probs={k: round(v, 4) for k, v in probs.items()},
            reason=(
                f"The model expects about {lam_h:.1f} goals for {home} and {lam_a:.1f} for {away}. "
                f"Chances: {home} {probs['HOME']:.0%}, draw {probs['DRAW']:.0%}, "
                f"{away} {probs['AWAY']:.0%}. "
                f"{home}'s attack is {_vs_avg(self.attack[home])} the league average and "
                f"{away}'s defence concedes {_vs_avg(self.defence[away])} average."
            ),
        )

    # ---- save / load ----
    def save(self, path: Path = MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "trained_at": datetime.now().isoformat(timespec="seconds"),
                    "trained_on": self.trained_on,
                    "mu_home": self.mu_home,
                    "mu_away": self.mu_away,
                    "rho": self.rho,
                    "draw_boost": self.draw_boost,
                    "home_adv": self.home_adv,
                    "attack": self.attack,
                    "defence": self.defence,
                    "games": self.games,
                }
            )
        )

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "PoissonModel | None":
        if not path.exists():
            return None
        d = json.loads(path.read_text())
        return cls(
            d["mu_home"], d["mu_away"], d["attack"], d["defence"], d["games"],
            d.get("rho", 0.0), d.get("draw_boost", 0.0), d.get("trained_on", 0), d.get("home_adv"),
        )
