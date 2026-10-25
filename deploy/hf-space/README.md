---
title: KhetSe API
emoji: 🌾
colorFrom: green
colorTo: orange
sdk: docker
app_port: 7860
pinned: false
short_description: KhetSe — Seedha Khet Se Ghar Tak (SIH26033) farm-to-buyer marketplace API
---

# KhetSe API

FastAPI backend for **KhetSe — Seedha Khet Se Ghar Tak**, a multi-sided agricultural
marketplace (Smart India Hackathon 2026, problem SIH26033, Team HexaScrapers).

- Interactive API docs: **`/docs`** (Swagger UI) once the Space is running
- Health check: **`/health`**
- Demo accounts (one-tap login via `POST /api/v1/auth/demo-login`): `farmer1`, `buyer1`, `driver1`, `fpo1`, `admin1`

## How this Space runs

- SDK `docker`, listening on port 7860.
- On startup it creates the schema on an embedded SQLite database, seeds a **clearly-labelled
  synthetic demo dataset** (farmers, FPO, listings, 14 days of mandi price observations, demo
  orders across the lifecycle) and starts serving.
- Storage is **ephemeral**: every Space restart resets to the same predictable demo state — that
  is intentional for a hackathon demo. For a persistent deployment, point `DATABASE_URL` at a
  managed Postgres (the app normalises bare `postgresql://` URLs) and add the Alembic migrations.

## Source

https://github.com/Venkatasai200628/khetse — 137 backend tests, honest labelling of every
simulated integration (payments sandbox, voice simulation), money stored as integer paise.
