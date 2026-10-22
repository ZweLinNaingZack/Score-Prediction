"""Find the model settings that predict best on matches the model has not seen.

    python -m app.ml.tune

Walk-forward test: for each block of recent matches, fit using only matches played BEFORE the block,
predict the block, then move on. That is how the model is used in real life, so the score is honest.
Settings are ranked by log loss (punishes over-confident wrong calls; the standard score for
probability forecasts). The best go to data/params.json and are used by app.ml.train.
"""
import json
import math
import sys
import time

from app.db.database import SessionLocal, init_db
from app.ml.model import PARAMS_PATH, Game, PoissonModel
from app.ml.train import MIN_GAMES_TO_TRAIN, load_games

TEST_SHARE = 0.30  # newest share of matches used as the test set
BLOCK = 150  # refit after this many test matches
HALF_LIVES = [250, 365, 550]
PRIORS = [2.0, 4.0, 8.0]
DRAW_BOOSTS = [0.0, 0.05]
HOME_PRIORS = [None, 5.0, 10.0, 20.0, 40.0]  # None = no per-team home advantage


def _outcome(h: int, a: int) -> str:
    return "HOME" if h > a else "AWAY" if h < a else "DRAW"


class Score:
    def __init__(self) -> None:
        self.n = self.hits = self.exact = 0
        self.log_loss = 0.0
        self.brier = 0.0

    def add(self, model: PoissonModel, g: Game) -> None:
        probs = model.outcome_probs(g.home, g.away)
        actual = _outcome(g.home_goals, g.away_goals)
        self.n += 1
        self.log_loss -= math.log(max(probs[actual], 1e-9))
        self.brier += sum((probs[k] - (k == actual)) ** 2 for k in probs)
        p = model.predict(g.home, g.away)
        self.hits += p.outcome == actual
        self.exact += (p.home_goals, p.away_goals) == (g.home_goals, g.away_goals)

    def summary(self) -> dict:
        n = max(self.n, 1)
        return {
            "n": self.n,
            "log_loss": self.log_loss / n,
            "brier": self.brier / n,
            "accuracy": self.hits / n,
            "exact": self.exact / n,
        }


def evaluate(games: list[Game], half_life: float, prior: float, variants: list[tuple[bool, float, float | None]]):
    """Walk-forward scores, one Score per (use_dc, draw_boost, home_prior) variant, sharing each fit."""
    scores = {v: Score() for v in variants}
    start = int(len(games) * (1 - TEST_SHARE))
    for b in range(start, len(games), BLOCK):
        train, block = games[:b], games[b : b + BLOCK]
        model = PoissonModel.fit(
            train, as_of=block[0].day, half_life_days=half_life, prior=prior, use_dc=True, home_prior=None
        )
        fitted_rho = model.rho
        for use_dc, boost, home_prior in variants:
            model.rho = fitted_rho if use_dc else 0.0
            model.draw_boost = boost
            if home_prior is None:
                model.home_adv = {}
            else:
                model.fit_home_advantage(train, block[0].day, half_life, home_prior)
            for g in block:
                if model.knows(g.home) and model.knows(g.away):
                    scores[(use_dc, boost, home_prior)].add(model, g)
    return {v: s.summary() for v, s in scores.items()}


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        games = load_games(db)
    finally:
        db.close()
    games.sort(key=lambda g: g.day)
    print(f"{len(games)} finished matches. Test set: newest {int(len(games) * TEST_SHARE)}, refit every {BLOCK}.")
    if len(games) < MIN_GAMES_TO_TRAIN:
        print("Not enough matches. Run: python -m scripts.backfill")
        return

    results = []
    variants = [(dc, b, hp) for dc in (False, True) for b in DRAW_BOOSTS for hp in HOME_PRIORS]
    t0 = time.time()
    for half_life in HALF_LIVES:
        for prior in PRIORS:
            for (dc, boost, hp), s in evaluate(games, half_life, prior, variants).items():
                results.append(
                    ({"half_life_days": float(half_life), "prior": prior, "use_dc": dc, "draw_boost": boost, "home_prior": hp}, s)
                )
            print(f"  half_life={half_life:4d} prior={prior:4.1f} done ({time.time() - t0:.0f}s)", flush=True)

    base = next(
        (s for p, s in results if p["half_life_days"] == 365.0 and p["prior"] == 4.0 and not p["use_dc"] and p["draw_boost"] == 0.0 and p["home_prior"] is None),
        None,
    ) or results[0][1]
    results.sort(key=lambda r: r[1]["log_loss"])

    def line(p, s):
        return (
            f"hl={p['half_life_days']:<5.0f} prior={p['prior']:<4} dc={str(p['use_dc']):5} boost={p['draw_boost']:<4} home={str(p['home_prior']):<5} | "
            f"log loss {s['log_loss']:.4f}  brier {s['brier']:.4f}  outcome {s['accuracy']:.1%}  exact {s['exact']:.1%}"
        )

    print("\nTop 8 by log loss:")
    for p, s in results[:8]:
        print("  " + line(p, s))
    print("Plain Poisson (hl 365, prior 4, no home advantage) for comparison:")
    print(f"  log loss {base['log_loss']:.4f}  brier {base['brier']:.4f}  outcome {base['accuracy']:.1%}  exact {base['exact']:.1%}")

    best_params, best = results[0]
    best_params = {**best_params, "log_loss": round(best["log_loss"], 4), "accuracy": round(best["accuracy"], 4),
                   "exact": round(best["exact"], 4), "tested_on": best["n"]}
    PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PARAMS_PATH.write_text(json.dumps(best_params, indent=2))
    print(f"\nSaved best settings to {PARAMS_PATH}")


if __name__ == "__main__":
    sys.exit(main())
