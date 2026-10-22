# Score Prediction App

Football match predictions from my own ML model plus Gemini, with an accuracy leaderboard. Match data comes from football-data.org.

## Backend setup (Windows)

    cd backend
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt   # on Python 3.15 xgboost/scikit-learn may lack wheels
    copy .env.example .env      # then add your football-data.org key
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000/docs to try the API. Run the tests with `python -m pytest`.

## Frontend

    cd frontend
    copy .env.local.example .env.local    # points the app at the backend
    npm run dev

Open http://localhost:3000. Without `NEXT_PUBLIC_API_URL` the app shows mock data.

## Data flow

- `GET /api/matches` refreshes from football-data.org when the cache is stale, then reads the
  database. Upcoming matches (next 9 days) refresh hourly and live scores every minute, but only
  while a stored match could be on. Each refresh is one request; the free tier allows 10 per minute.
  Tune `LIVE_CACHE_SECONDS` / `UPCOMING_CACHE_SECONDS` in `.env`.
- The free tier covers the Premier League, La Liga, Serie A, Bundesliga, Ligue 1 and the Champions
  League. Europa League and Nations League stay empty until a source that covers them is added.
- `python -m scripts.fetch_and_predict` saves my model and Gemini predictions for matches
  in the next 48h (needs each provider's key in `.env`).
- `python -m scripts.update_results` stores final scores for finished matches.
- `GET /api/leaderboard` is computed from stored predictions and results.

## Structure

    backend/
      app/
        main.py               FastAPI entry point
        config.py             settings loaded from .env
        api/routes.py         HTTP endpoints
        services/football_data.py   football-data.org client
        llm/                  Gemini (and optional GPT, Grok, Claude) predictors
        ml/                   your own model (train.py, model.py)
        db/                   database and tables
      scripts/                daily jobs: predict before matches, record results after
      data/                   SQLite database and saved models
    frontend/                 Next.js app
