# Score Prediction App

Football match predictions from our own statistical model, shown next to
live and upcoming matches, with an accuracy leaderboard. Match data comes from football-data.org.

Windows machine, PowerShell/Git Bash. Not a git repository. Python 3.15 (very new: some wheels are
missing, see Gotchas).

## Layout

    backend/    FastAPI + SQLAlchemy (SQLite). Python venv in backend/.venv
    frontend/   Next.js 16 (App Router) + Tailwind 4. Read frontend/AGENTS.md first.

Key backend files:

    app/main.py                  FastAPI entry, CORS allow-all, init_db on startup
    app/config.py                Settings from backend/.env
    app/leagues.py               football-data.org code -> frontend league id; SOURCE_TO_MODEL
    app/schemas.py               Response models, camelCase on the wire
    app/api/routes.py            health, matches, leaderboard, standings/{league}, auth, unlock
    app/services/football_data.py   API client (one function per endpoint)
    app/services/sync.py         API -> DB: mapping, upsert, TTL cache, live window
    app/services/matches.py      DB -> response (match list, leaderboard)
    app/llm/                     Shared prompt + one predictor per provider
    app/ml/                      Our model: model.py, train.py, tune.py (settings search)
    scripts/fetch_and_predict.py Saves my_model + LLM predictions for matches in the next 48h
    scripts/update_results.py    Stores final scores for finished matches
    scripts/backfill.py          Loads past seasons so the model has training data
    tests/                       pytest, uses a temp SQLite file and faked network

Key frontend files:

    lib/types.ts        Match / Prediction / LeaderboardEntry. Must match backend/app/schemas.py
    lib/leagues.ts      League list (id, name, short, category) and model labels
    lib/hot.ts          "Hottest" ranking for the landing page
    lib/api.ts          fetchMatches / fetchLeaderboard. Mock data unless NEXT_PUBLIC_API_URL is set
    lib/mock.ts         Demo data (used when no API URL is set)
    lib/useMatches.ts   Client hook, refetches every 30s
    components/         Landing, MatchCard, MatchRow, MatchesBoard, StandingsBoard, Leaderboard, Header, ...
    app/                / (landing), /matches, /league/[id], /match/[id], /table, /leaderboard (track record), /login

## Run it

Two programs must run at the same time, each in its own terminal.

    # backend
    cd backend
    .venv\Scripts\activate
    uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs

    # frontend
    cd frontend
    npm run dev                          # http://localhost:3000

Checks:

    cd backend  && .venv\Scripts\python -m pytest -q
    cd frontend && npx tsc --noEmit && npx eslint && npx next build

Daily jobs (run from backend/, venv active):

    python -m scripts.fetch_and_predict
    python -m scripts.update_results

## Configuration

`backend/.env` (gitignored; template is `.env.example`, never put real keys in the template):

    FOOTBALL_DATA_KEY=      required for real matches
    OPENAI_API_KEY=         optional, each blank provider is skipped
    GEMINI_API_KEY=
    XAI_API_KEY=            Grok
    ANTHROPIC_API_KEY=
    DATABASE_URL=sqlite:///./data/app.db
    AUTH_SECRET=            optional, signs login tokens (random file used if blank)
    PREDICT_HOURS_AHEAD=48       (optional override)
    LLM_MAX_PER_RUN=10 / LLM_PAUSE_SECONDS=7   (optional, free-tier quota guards)
    LIVE_CACHE_SECONDS=60        (optional override)
    UPCOMING_CACHE_SECONDS=3600  (optional override)

`frontend/.env.local` (gitignored; template is `.env.local.example`):

    NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api

Delete `.env.local` to fall back to mock data. The backend reads `.env` only at startup, so restart
it after changing a key (`--reload` does not re-read `.env`).

## How data flows

1. `GET /api/matches` calls `sync.refresh_if_stale`, then reads the database.
2. Upcoming matches (next 9 days, API limit is 10) refresh at most hourly: one request.
3. Live scores refresh at most every 60s, and only while a stored match is live or could have
   started in the last 3h (`live_window_open`). One request.
4. A match that disappears from the live feed gets its final state fetched by id.
5. API failures are logged and never raised to the page. Stale data is served and the refresh
   retries after 5 minutes.
6. Postponed/cancelled matches are deleted (with their predictions) so they don't linger as upcoming.
7. Predictions are NOT made on web requests (each is a paid call). `fetch_and_predict` writes them.
8. `/api/matches` returns: live, upcoming, and finished within the last 3 days. Each match carries
   the latest prediction per source. `/api/leaderboard` counts exact scores and correct outcomes over
   finished matches, listing all five models even at zero.

Time: all kickoffs are stored as naive UTC and returned as ISO with a trailing `Z`.

## Data source: football-data.org (free tier)

- Limit is 10 requests/minute, not per day.
- Covered: Premier League (PL), La Liga (PD), Serie A (SA), Bundesliga (BL1), Ligue 1 (FL1),
  Champions League (CL).
- NOT covered: Europa League and Nations League. Their cards exist in the UI (ids 3 and 5) but stay
  empty. Fix with a paid plan or a second source.
- Frontend league ids are the old API-Football ids (39, 140, 135, 78, 61, 2, 3, 5), kept stable.
  `app/leagues.py` maps football-data codes onto them. Add a league in both `app/leagues.py` and
  `frontend/lib/leagues.ts`.
- Free-tier live scores may be delayed, and the live `minute` field may be missing. The UI shows
  "Live" without a minute when it is null. Not yet verified against a real live match.
- We moved here from API-Football because its free plan only covers seasons 2022 to 2024 and blocks
  the `next` parameter. It also returns HTTP 200 with the error in the body, which is why the old
  code returned an empty list silently.

## Dates and logos

- League pages (`/league/[id]`) show a date strip (3 days back to 9 ahead, `DateStrip.tsx`),
  default today. Days use the viewer's local timezone. Empty day shows "No matches on this day."
  The strip only renders after matches load, which avoids a hydration mismatch.
- Team logos come from football-data.org `crest` URLs, stored as `home_crest`/`away_crest` on
  Fixture. `TeamCrest.tsx` falls back to the 3-letter code if missing or broken. Old finished rows
  have no crest until refreshed. `init_db` adds new nullable columns itself (`_add_missing_columns`).

## Match list, match page, lock

- Lists (`MatchesBoard`) are rows (`MatchListItem`) that link to `/match/[id]` (`MatchDetail.tsx`).
  Cards and rows elsewhere show no predictions. The id comes from the server page as a prop (not
  `useParams`, which breaks the cacheComponents build). `generateStaticParams` returns a dummy id.
- **Real lock (server side).** `GET /api/matches` only includes `predictions` for matches the
  signed-in user unlocked; everyone else gets `predictions: []`, `unlocked: false`, plus
  `predictionModels` (who predicted, no scores). `POST /api/matches/{id}/unlock` (needs login)
  records a row in `unlocks`. Leaderboard stays public (counts only). Unlocking is free: there is no
  payment yet. Put a payment/credit check inside the `unlock` route in `app/api/routes.py`.
- Accounts: `POST /api/auth/register|login` return a token, `GET /api/auth/me`. `app/auth.py` is
  stdlib only (scrypt passwords, HMAC-signed tokens, 30 days). Secret: `AUTH_SECRET` in `.env`, or a
  random one saved in `backend/data/.auth_secret`.
  Password rule (server `password_problem` and the checklist in `AuthForm.tsx`, keep in sync): 8+
  characters with a lowercase, a capital, a number and a symbol.
  Login limit: 5 wrong tries per address+email, then a 5 minute lock (HTTP 429 with Retry-After); 20
  wrong tries across emails from one address also locks it. Counts are in memory (`LoginLimiter`):
  they reset on restart and are per process. Behind a proxy every user shares the proxy address, so
  read the real client IP first. Not done: password reset, email verification.
- Sign-up asks for a name (2-40 chars, `users.name`; older accounts fall back to the email before the @).
  Header shows the name, not the email. Login/register/me all return `name`.
- League logos: `League.logo` in frontend/lib/leagues.ts (football-data.org emblem URLs, on a white plate by
  `LeagueLogo.tsx`). Nations League has no logo and shows its code. Logos are not lazy-loaded.
- Frontend: token in localStorage (`lib/auth.ts`, `useSession`), sent as a Bearer header by
  `lib/api.ts`. `/login` page, `AccountLink` in the header. In mock mode (no API URL) the unlock
  button just reveals the demo predictions.
- Each prediction has a `reason`. my_model builds it from its own numbers (no AI). LLMs return it in
  the same JSON reply (`build_prompt`). Stored in `predictions.reason`.
- `fetch_and_predict`: my_model predicts EVERY upcoming match (free). AI providers only get matches
  within `PREDICT_HOURS_AHEAD` (default 48), soonest first, at most `LLM_MAX_PER_RUN` (10) calls per
  run, `LLM_PAUSE_SECONDS` (7) apart, and a provider stops for the run on a 429 quota error. Each
  match+source is predicted once. Visitors and the Unlock button never call an AI.

## Market odds (The Odds API)

- Free key at the-odds-api.com (500 credits/month) in `ODDS_API_KEY`. `python -m scripts.update_odds` costs
  1 credit per league with matches in the next 7 days (about 6 per run, so twice a day is ~360/month).
  Web requests never call the API. It prints credits left and matches it could not pair.
- `app/services/odds.py`: consensus over bookmakers (average odds; chances with the margin removed),
  and matching to our fixtures by kickoff (within 3h) plus team-name similarity (word based, small
  alias list: add entries to `ALIASES` when the script reports unmatched matches).
- Public: `odds` on every match (match page "Market odds" tiles, small 1/X/2 chip in list rows from md up).
  Inside Unlock: `predictions[].chances` (our model chances, saved in `predictions.prob_*`) feed the
  "Market vs our model" card. No bookmaker names or links anywhere, on purpose. Sport keys are in
  `LEAGUE_ID_TO_ODDS_KEY` (app/leagues.py), checked against the free /sports call on each run.
- Predictions made before 2026-10-22 have no `chances` (the card hides).
- Run against the real API (2026-10-23): 56 of 56 upcoming matches paired after adding aliases for Barca,
  HSV and Rennais (spelled differently in the odds feed). Model and market chances differ by 3.9
  points on average. Free credits: 500/month, about 5 used per run.

## Frontend design

Dark-only "OLED" look chosen with the ui-ux-pro-max skill (in `C:\zwe lin naing\UI UX max skill`):
pure black background, gold accent (`--accent`), red only for live (`--live`), hairline borders.

- Font: Segoe UI first, Open Sans (next/font) as fallback on other systems. Geist Mono for the
  prediction scores. This was chosen to match a screenshot the user liked. Do not reintroduce
  Bebas Neue or Source Sans.
- Colors are semantic tokens in `app/globals.css` (`bg-surface`, `text-muted`, `border-line`,
  `text-accent`, `text-live`). Use them, not raw hex.
- Landing page order: hero, "Choose a league" cards, "Hottest live" (top 5, #1 is a large featured
  card), "Hottest upcoming" (top 5 ranked rows).
- "Hottest" is a guess in `lib/hot.ts`: league prestige weight, plus goals/close game/late minute
  for live, plus kickoff proximity within 48h for upcoming. Tune the weights if picks feel off.
- Accessibility rules applied: skip link, visible gold focus ring, 44px touch targets,
  `aria-current` on nav, `aria-pressed` on filters, reduced-motion support, tabular numerals.

## Deployment (LIVE 2026-10-24: https://score-prediction-tau.vercel.app, API https://score-prediction-api.onrender.com/api)

- Vercel needs root directory `frontend` and env `NEXT_PUBLIC_API_URL` (built in: redeploy after changing it).
  Render `CORS_ORIGINS` must be the Vercel origin; `parse_origins` (app/main.py) forgives quotes, a trailing
  slash and a missing https://. A wrong value shows as a CORS error in the browser console and "Can't load".

- See DEPLOY.md. Vercel = `frontend/` (root dir setting, env `NEXT_PUBLIC_API_URL`), Render = `render.yaml`
  (backend/, Python 3.13, `--proxy-headers` so the login limiter sees real client addresses), Neon = Postgres.
- `DATABASE_URL` may be `postgresql://...`: `normalize_database_url` (app/db/database.py) adds the psycopg
  driver. Checked against the real Neon database (2026-10-23): connects, creates all 6 tables, a second
  init_db is harmless, and the reserved-word column `group` round-trips. Live API: https://score-prediction-api.onrender.com/api
  (free Render, sleeps when idle). First-time setup workflow ran green; the live API then served 85 matches,
  predictions for all 62 upcoming and odds for 56. Lesson: GitHub and Render each hold their own copy of
  `DATABASE_URL`; when they differed the jobs filled one database and the API read another. `CORS_ORIGINS` limits browser access (default `*`).
- Daily jobs run in GitHub Actions (`.github/workflows/jobs.yml`), not on Render: update_results, train,
  fetch_and_predict, update_odds, writing to Neon. The model is retrained inside each run, so
  `data/model.json` on the API server is never used. `bootstrap.yml` is the one-time backfill. `ci.yml` runs tests.
- Requirements are split: requirements.txt (production), -dev (pytest), -ai (optional AI SDKs).

## Next.js 16 notes (this is not the Next.js from older training data)

- `next.config.ts` has `cacheComponents: true`. Uncached server data must be inside `<Suspense>`.
  We avoid the issue by fetching on the client in `useMatches`; pages are thin server shells.
- Route props are typed globally: `PageProps<"/league/[id]">`, `LayoutProps<"/">`. `params` is a
  Promise. These types are generated at build, so run `next build` once before `tsc` on a fresh
  checkout or tsc reports "does not satisfy AppRoutes".
- Docs are bundled at `frontend/node_modules/next/dist/docs/`.
- `/league/<unknown id>` returns HTTP 200 with the not-found UI (page streams before notFound()).

## Gotchas

- `uvicorn[standard]` fails to install on Python 3.15 (PyYAML has no wheel). Use plain `uvicorn`.
- Requirements are split (see Deployment). Installed in `backend/.venv`: web packages (fastapi, uvicorn, httpx, python-dotenv,
  pydantic-settings, sqlalchemy, pytest) and the AI SDKs (openai, google-genai, anthropic).
  pandas, scikit-learn, xgboost are in requirements.txt but NOT installed (the Poisson model does
  not need them); they may lack Python 3.15 wheels.
- The database uses `create_all`, which never alters existing tables. After changing
  `app/db/models.py`, delete `backend/data/app.db` (it repopulates from the API).
- When appending to `.env` from a script, check the file ends with a newline first, or the new
  variable fuses onto the last line.
- On Windows, `pkill` does not stop a background uvicorn. A leftover server keeps port 8000 and
  keeps old settings. Find it with `Get-NetTCPConnection -LocalPort 8000` and `Stop-Process`.
- Do not print or paste API keys. Check `.env` with a masking command, for example
  `sed -E 's/=.+/=<set>/' .env`.

## Status

Done:
- Frontend: landing, /matches, /league/[id], /leaderboard, all connected to the backend.
- Backend: football-data.org sync, /api/matches, /api/leaderboard, scripts, accounts + server-side unlock, 16 passing tests.
- Verified against the real API: 92 upcoming matches across 6 leagues.
- ML model (2026-10-22): Dixon-Coles style Poisson with time decay, shrinkage and per-team home
  advantage, trained on 6,156 finished matches (seasons 2023-2026; the free tier blocks 2022 and
  older). Walk-forward test on 1,798 unseen matches: outcome 52.6%, exact score 10.1%, log loss
  0.9848 (plain Poisson 0.9880; always-home 45%). Tried and rejected (no gain): short-term form
  blend, probability calibration, rest days, draw boost. Settings live in `backend/data/params.json`
  (written by `python -m app.ml.tune`, ~3 min; the best of 120 configs on the same test set, so
  slightly optimistic). Retrain after new results: `python -m app.ml.train`.
- League tables: `/table` for PL, La Liga, Serie A, Bundesliga, Ligue 1 and the Champions League
  (36-team league phase). `GET /api/standings/{leagueId}`, cached 30 min (`STANDINGS_CACHE_SECONDS`),
  one football-data.org request per league; form dots come from stored finished matches. Zone colours
  (top 4, relegation, CL last 16/play-offs) are in `zoneFor` (frontend/lib/leagues.ts) and are
  approximate: check them against the season rules.
- AI keys were removed on purpose; only our own model is used (see Decision above). `/leaderboard`
  is now a "Track record" page for that one model.
- Checked in a browser (2026-10-22) at desktop and 375px: league list rows, date strip, empty day,
  logos, match page, unlock button and the "Why" text.

Not done / next:
- **Decision (2026-10-22): portfolio project, no AI providers.** Only our own model is used and every AI
  key was removed from `.env`. The AI code (`app/llm`, `scripts/check_providers.py`, SDKs in the venv) is
  kept but inactive. To bring a provider back: add it to `SOURCE_TO_MODEL` (backend/app/leagues.py) and
  `MODELS` (frontend/lib/leagues.ts) and set its key. Gemini worked with gemini-3.8-flash (free tier
  often returns 503, `predict_gemini` retries). Override model names with *_MODEL vars in `.env`.
- Scheduling for the two scripts (Windows Task Scheduler or similar).
- Europa League and Nations League data.
- Verify live scores and the `minute` field during a real live match.
- Visual check of the UI in a browser at 375px and desktop. Only build/lint/HTTP checks were done.
