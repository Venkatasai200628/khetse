# KhetSe — Seedha Khet Se Ghar Tak

A multi-sided agricultural marketplace connecting farmers directly with households, retailers, hotels and institutional buyers — with voice-first listings, fair-price recommendations from real mandi data, shared logistics with QR-verified delivery, and transparent payment settlement.

- **Problem Statement:** SIH26033 — intermediaries reduce farmers' earnings and increase consumer prices
- **Theme:** Agriculture, FoodTech & Rural Development · **Team:** HexaScrapers
- Full requirements analysis: see [`ANALYSIS.md`](./ANALYSIS.md)

## Stack

| Layer | Technology |
|---|---|
| Mobile / Web | Flutter (Android-first), Riverpod, GoRouter, Dio |
| Backend | FastAPI (Python 3.12+), Pydantic v2 |
| Database | PostgreSQL (+ Alembic migrations); Redis (cache/rate limits, optional) |
| AI / Data | pandas, scikit-learn, LightGBM, Google OR-Tools, Bhashini ASR |
| Infra | Docker Compose, GitHub Actions |

## Repository layout

```
├── app/        # Flutter application
├── backend/    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/       # route handlers
│   │   ├── core/         # config, security, errors, logging
│   │   ├── db/           # session, base, seed (demo data)
│   │   ├── models/       # SQLAlchemy models (44-table schema)
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # business logic
│   │   ├── integrations/ # external provider adapters (+ mocks)
│   │   ├── ai/           # pricing, forecasting, quality, routing
│   │   └── tasks/        # background jobs
│   ├── alembic/          # migrations
│   └── tests/
├── docs/       # architecture, diagrams, demo guide
└── docker-compose.yml
```

## Quickstart (local development)

Prerequisites: Python 3.12+, Docker (for PostgreSQL/Redis), Flutter SDK (for the app).

```bash
# 1. Environment file
cp .env.example .env          # then edit JWT_SECRET at minimum

# 2. Start PostgreSQL + Redis
docker compose up -d db redis

# 3. Backend
py -3.13 -m venv .venv                          # Windows (or: python3.12 -m venv .venv)
.venv/Scripts/python -m pip install -r backend/requirements.txt   # Windows
# .venv/bin/pip install -r backend/requirements.txt               # Linux/macOS

cd backend
../.venv/Scripts/python -m alembic upgrade head    # apply migrations
../.venv/Scripts/python -m uvicorn app.main:app --reload   # http://localhost:8000/docs
```

### Seed demo data

```bash
cd backend
../.venv/Scripts/python -m app.db.seed     # demo users, FPO, 8 commodities, 10 listings, market data, 5 orders (all synthetic, labelled)
```

Idempotent — safe to re-run. Creates demo accounts with one-tap logins
(`farmer1`, `buyer1`, `driver1`, `fpo1`, `admin1` via
`POST /api/v1/auth/demo-login`, available while `DEMO_MODE=true`), a demo
FPO with its collection centre, the commodity catalogue (English + Telugu),
10 synthetic listings, 14 days of synthetic mandi price observations, and
demo orders spanning the lifecycle (payment_pending, confirmed,
out_for_delivery, completed, cancelled).

### Run tests

```bash
cd backend
../.venv/Scripts/python -m pytest -v
```

## Flutter app

```bash
cd app
flutter pub get
flutter run                  # attached device / emulator
flutter run -d chrome        # web
flutter build apk --release  # Android APK
```

## External integrations

| Integration | Mode | Configuration |
|---|---|---|
| Agmarknet mandi prices | Real (data.gov.in API key) or seeded | `DATA_GOV_IN_API_KEY` |
| Bhashini speech (ASR/TTS) | Real (ULCA key) or simulated | `BHASHINI_API_KEY` |
| OSRM routing | Real (public demo server / self-host) | `OSRM_BASE_URL` |
| Weather | Open-Meteo (free) or IMD | `WEATHER_PROVIDER` |
| Payments | Mock sandbox by default | `PAYMENT_PROVIDER` |
| SMS / Voice | Mock (in-app + logs) | `SMS_PROVIDER` |

Every adapter implements the same interface for real and mock providers; the mock is used automatically when credentials are absent and is **always clearly labelled** in the UI and API responses. No external transaction is ever faked as real.

## Security notes

- Auth: phone + OTP (JWT sessions). Development OTP delivery is available **only** when `ENV != production`.
- Role-based access enforced server-side on every endpoint; ownership checks on all resources.
- Money is stored as integer minor units (paise); no floating-point arithmetic in financial code.
- Idempotent checkout with buyer-scoped keys; an explicit order state machine with audited transitions; OTP rate limiting.
- Secrets live only in `.env` (never committed); production error responses never leak stack traces.

See [docs/security.md](docs/security.md) for the full policy.
