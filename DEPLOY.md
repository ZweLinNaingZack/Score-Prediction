# Deploying

Three free services, each with a job:

| Part | Where | What it does |
|---|---|---|
| Website | **Vercel** | The Next.js app in `frontend/` |
| API | **Render** | The FastAPI app in `backend/` (`render.yaml`) |
| Database | **Neon** | Postgres: matches, predictions, odds, accounts |
| Daily jobs | **GitHub Actions** | Scores, retraining, predictions, odds (`.github/workflows/jobs.yml`) |

Do the steps in this order. Keep a notepad open: you copy a few addresses between services.

## 1. Neon (database)

1. neon.com > sign up > **Create project**. Pick the AWS **Singapore** region (same region you will give Render).
2. On the project page click **Connect**, copy the connection string. It looks like
   `postgresql://user:password@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
   This is your `DATABASE_URL`. Treat it like a password.

## 2. GitHub secrets (for the daily jobs)

Repo > **Settings > Secrets and variables > Actions > New repository secret**. Add three:

- `DATABASE_URL` (from Neon)
- `FOOTBALL_DATA_KEY` (same value as in `backend/.env`)
- `ODDS_API_KEY` (same value as in `backend/.env`)

## 3. Fill the database once

Repo > **Actions > First-time setup > Run workflow**. It takes about 5 minutes: it loads four seasons of
results, trains the model, makes predictions and fetches odds. Open the run and check each step is green.
After this the **Daily jobs** workflow keeps everything fresh (05:15 and 17:15 UTC). You can also run it by
hand from the Actions tab.

## 4. Render (API)

1. render.com > **New > Blueprint** > pick this repo. It reads `render.yaml`.
2. It asks for three values: `DATABASE_URL` (Neon), `FOOTBALL_DATA_KEY`, and `CORS_ORIGINS`.
   For `CORS_ORIGINS` type `*` for now. You tighten it in step 6.
3. Wait for the deploy. Open `https://<your-service>.onrender.com/api/health`. You should see `{"status":"ok"}`.
   Then open `/api/matches`: you should see matches.

## 5. Vercel (website)

1. vercel.com > **Add New > Project** > import this repo.
2. **Root Directory: `frontend`** (click Edit next to it). Framework is detected as Next.js.
3. **Environment Variables**: name `NEXT_PUBLIC_API_URL`, value `https://<your-service>.onrender.com/api`
   (ends with `/api`, no trailing slash).
4. **Deploy.** Copy the address Vercel gives you, e.g. `https://score-prediction.vercel.app`.

## 6. Lock the API to your website

Render > your service > **Environment** > set `CORS_ORIGINS` to your Vercel address
(no trailing slash). Save: Render restarts the service.

## Good to know

- **Free Render sleeps** after 15 minutes without visitors. The first visit afterwards takes 30-60 seconds and
  the site shows "Can't reach the API" for a moment. The daily jobs do not need Render, they talk to Neon.
- The login lock (5 wrong tries) is kept in memory, so it resets when Render sleeps or restarts.
- GitHub pauses scheduled workflows after 60 days with no commits to the repo. Push any commit or press
  **Enable workflow** to resume.
- The Odds API free plan is 500 credits a month. Two runs a day uses about 300.
- Changed `NEXT_PUBLIC_API_URL`? Redeploy on Vercel: it is baked in when the site is built.

## Troubleshooting

| What you see | Likely cause |
|---|---|
| "Demo data" line on the site | `NEXT_PUBLIC_API_URL` was not set when Vercel built. Set it, then **Redeploy**. |
| Browser console: CORS error | `CORS_ORIGINS` on Render does not match your Vercel address exactly. |
| Matches empty, health is ok | The first-time setup workflow did not finish, or `FOOTBALL_DATA_KEY` is wrong. |
| No predictions on matches | Run **Daily jobs** by hand and read the "Predict" step. |
| Everyone gets locked out of login | Render needs the `--proxy-headers` start command (already in `render.yaml`). |
