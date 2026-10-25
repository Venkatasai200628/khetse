# Deploying KhetSe

## Frontend (Flutter web) — Vercel

The web build is a static bundle, so any static host works. With the Vercel CLI:

```bash
cd app
flutter build web --release --dart-define=API_BASE_URL=https://<your-backend-host>/api/v1
npx vercel deploy build/web --prod
```

`API_BASE_URL` is baked in at build time (see `app/lib/core/config/app_config.dart`).
Rebuild and redeploy whenever the backend URL changes.

Alternatives: GitHub Pages (hash routing, no rewrites needed) or Netlify — same build, same
static directory.

## Backend — Render (recommended free tier)

1. Push this repo to GitHub (already at github.com/Venkatasai200628/khetse).
2. In Render: **New + → Blueprint**, select the repository. Render reads `render.yaml`:
   a free web service (Docker, `backend/Dockerfile`) + a free PostgreSQL database.
3. Migrations run automatically at container start (`alembic upgrade head` in the Dockerfile CMD).
4. Seed demo data once from your machine against the Render database:
   ```bash
   DATABASE_URL="<render-internal-connection-string>" python -m app.db.seed
   ```
   (run from `backend/` with the project venv).
5. Point the frontend build at `https://khetse-api.onrender.com/api/v1`.

Notes:
- Render's free plan spins the service down after inactivity; the first request then takes ~30s.
- The free database expires after 30 days — recreate it, or point `DATABASE_URL` at a free
  Neon/Supabase Postgres instead (the app normalises `postgresql://` URLs automatically).
- `CORS_ORIGINS=*` in `render.yaml` is a demo loosening; set it to your frontend origin for anything real.

## Backend — Hugging Face Spaces (alternative free host)

**Update (2026-10-25):** HF now requires a **PRO subscription** for Docker and Gradio Spaces on
free cpu-basic hardware (the API returns `402 Payment Required`). Only Static Spaces are free,
and those cannot run a backend. If you have PRO, the definition in `deploy/hf-space/`
(README metadata + Dockerfile) works as-is:

```bash
# assemble the staging dir (copies backend/app + requirements.txt alongside the Dockerfile)
bash deploy/hf-space/build.sh
hf repo create <user>/khetse-api --repo-type space --space-sdk docker
hf upload <user>/khetse-api deploy/hf-space/staging . --repo-type space
```

The Dockerfile listens on port 7860, creates the schema on embedded SQLite, and re-seeds the
labelled demo dataset at every startup.

## Interim demo tunnel (zero setup)

While the backend still runs on a laptop:

```bash
cloudflared tunnel --url http://localhost:8000
```

gives a public `https://<random>.trycloudflare.com` URL with no signup. The URL **changes every
time the tunnel restarts**, so the frontend must be rebuilt with the new `API_BASE_URL`. Good for
a live demo, not for a standing deployment.
