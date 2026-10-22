"""Competitions the app tracks. Frontend league ids (frontend/lib/leagues.ts) are kept stable,
so football-data.org codes are mapped onto them.

Europa League (3) and Nations League (5) are shown in the UI but are not on football-data.org's
free tier, so they stay empty until a plan or source that covers them is added.
"""

COMPETITION_TO_LEAGUE_ID = {
    "PL": 39,   # Premier League
    "PD": 140,  # La Liga
    "SA": 135,  # Serie A
    "BL1": 78,  # Bundesliga
    "FL1": 61,  # Ligue 1
    "CL": 2,    # Champions League
}
COMPETITION_CODES = list(COMPETITION_TO_LEAGUE_ID)
LEAGUE_ID_TO_CODE = {v: k for k, v in COMPETITION_TO_LEAGUE_ID.items()}

# frontend league id -> The Odds API sport key (script checks them against its /sports list)
LEAGUE_ID_TO_ODDS_KEY = {
    39: "soccer_epl",
    140: "soccer_spain_la_liga",
    135: "soccer_italy_serie_a",
    78: "soccer_germany_bundesliga",
    61: "soccer_france_ligue_one",
    2: "soccer_uefa_champs_league",
}

# DB `source` value -> model id used by the frontend. Only models listed here are shown and ranked.
# Portfolio setup: our own model only (no paid or quota-limited AI). The AI predictor code in
# app/llm stays; to bring a provider back, add it here (e.g. "gemini": "gemini") and to MODELS in
# frontend/lib/leagues.ts, and set its key in .env.
SOURCE_TO_MODEL = {
    "my_model": "ml",
}
