# KhetSe — Complete Analysis & Clarity Document

> **Problem Statement:** SIH26033 — "Multiple intermediaries reduce farmers' earnings and increase consumer prices"
> **Theme:** Agriculture, FoodTech & Rural Development · **Team:** HexaScrapers · **Target:** Smart India Hackathon 2026
> **Analysis date:** 2026-10-25 · All external-service statuses verified on this date.

---

## 1. What this project is — the 60-second version

**KhetSe ("Seedha Khet Se Ghar Tak") is a multi-sided marketplace app that lets farmers sell produce directly to households, shops, hotels and institutions — cutting intermediary layers — with AI-assisted pricing, voice-based listing (for low-literacy farmers), shared delivery logistics with QR-verified handoffs, and transparent payment settlement.**

The pitch in one flow:

```
Farmer speaks "500 kg tomatoes, ₹20/kg" (in Telugu/Hindi)
      → app transcribes & shows a confirm form + fair-price benchmark (real Agmarknet mandi data)
      → listing goes live → buyer orders & pays (sandbox)
      → FPO aggregates nearby orders into one delivery run (OR-Tools optimised route)
      → driver picks up, QR-scans at each checkpoint, delivers
      → payment splits visibly: farmer gross / delivery / platform fee
      → every step traceable in the admin dashboard
```

**Core principle the spec repeats everywhere:** traceability from farm listing → order → pickup → delivery → payment → settlement, and **never fake anything** (no fake payments, no invented AI accuracy numbers, no mockups pretending to be real integrations).

---

## 2. The 6 roles (one line each)

| Role | Who they are | Their single core job in the app |
|---|---|---|
| **Farmer** | Producer, low digital literacy | List produce by voice + photo, see fair price, accept/reject offers, track earnings |
| **Household Buyer** | Families | Browse, cart, checkout, weekly basket, review after delivery |
| **Business Buyer** | Kirana / hotel / canteen / institution | Bulk orders, recurring supply, RFQ (request-for-quote) flow |
| **Driver** | Verified transport | Pickup/delivery batches, optimised stop sequence, QR confirm, exception reports |
| **FPO / Collection Centre** | Farmer Producer Org staff | Onboard & verify farmers, weigh/grade intake, aggregate orders, crate QR labels, dispatch |
| **Admin** | Platform operators | Verifications, market-data quality, fee config, disputes, audit log, analytics |

Key rule: **permissions are enforced on the backend**, not just hidden in the UI. Drivers never see farmer/buyer personal details they don't need.

---

## 3. The 6 core workflows (the heart of the build)

1. **Voice listing** — tap "Speak to Sell" → mic permission → speak in Telugu/Hindi/English → transcript → structured extraction (crop, qty, unit, price, date) → editable confirm form (never auto-publish low-confidence results) → price recommendation with source & date → publish. Manual entry fallback always available.
2. **Order & acceptance** — buyer orders → farmer/FPO notified → accept/reject → inventory reserved (DB transaction + idempotency keys, no overselling) → total + delivery fee computed server-side → payment → tracked status. Cancellation/refund rules consistent.
3. **Shared logistics** — group compatible orders → OR-Tools vehicle routing (capacity, time windows, pickup-before-dropoff) → OSRM road distances → driver + manifest (stops, order IDs, crate labels) → pickup quantity verification → delivery with QR → exception logging. Nearest-neighbour fallback if solver unavailable.
4. **QR verification** — unpredictable QR IDs linked to shipment/order records (no personal data inside the QR) → authenticate actor → validate order state → confirm qty → record timestamp/actor/method → replay-proof → audit event. Manual fallback for damaged labels.
5. **Payment & settlement** — payment-provider abstraction (initiate → signed webhook → reconcile → idempotent webhook handling → ledger entries → farmer/driver payouts → platform fee → refunds). **Spec red line:** never hold customer money in a normal bank account and call it "escrow" — use provider-supported split/settlement or a clearly-labelled sandbox. A payment is never "successful" just because a button was clicked.
6. **Notifications (SMS/voice)** — listing confirmations, offer alerts, pickup reminders, payment status, grievance acks — in the user's language, with retry limits, consent checks, delivery logs. In-app notifications + simulated SMS/voice in demo mode.

**Order state machine (must be explicit, validated, audited):**

```
CREATED → AWAITING_FARMER_CONFIRMATION → ACCEPTED → PAYMENT_PENDING → CONFIRMED
        → PICKUP_SCHEDULED → PICKED_UP → OUT_FOR_DELIVERY → DELIVERED → COMPLETED

Exception states: REJECTED · CANCELLED · PAYMENT_FAILED · REFUND_PENDING · REFUNDED
                 · DELIVERY_FAILED · DISPUTED
```

Payment status is tracked **separately** from order status — "delivered" ≠ "settled".

---

## 4. Tech stack at a glance

| Layer | Choice | Notes |
|---|---|---|
| Mobile/Web app | **Flutter (Dart)**, Material 3 | Android-first, web-compatible; Riverpod + GoRouter + Dio; secure token storage; offline cache & queued actions |
| Backend | **FastAPI (Python 3.12)** + Pydantic v2 | Backend owns ALL validation, pricing, order transitions, stock, financial records |
| Database | **PostgreSQL** (+PostGIS optional) | 43 tables, Alembic migrations; money in integer minor units (paise) — never floats |
| Cache/jobs | **Redis** + Celery (where available) | Rate limiting, background imports/forecasting |
| AI/ML | pandas, scikit-learn, **LightGBM**, optional Prophet; OR-Tools for routing | Bhashini/AI4Bharat for speech; OpenCV/Pillow for images |
| DevOps | Docker Compose, GitHub Actions, `.env` + `.env.example` | Pinned deps, structured logging, OpenAPI docs auto-generated |

**Design system:** agricultural green `#138A4B` dominant, harvest orange `#F58A24` accents, cream `#F8F8F2`/white surfaces; Inter (Latin) + Noto Sans (Indic/Telugu); rounded cards 12–18px, ≥48px touch targets, spacing scale 4/8/12/16/24/32. Original leaf/field logo — never reuse the SIH logo.

**Languages:** English + Telugu first, Hindi + other Indic structured for extension.

---

## 5. The AI modules — what is actually ML vs rules vs mock

| Module | Reality for the MVP |
|---|---|
| **Speech recognition** | Real via **Bhashini cloud API** (Telugu/Hindi supported). ASR ≠ extraction — a separate parser pulls crop/qty/unit/price from the transcript and asks the farmer to confirm. Never guesses missing numbers. |
| **Structured extraction** | Deterministic parsing + validation (rules), confidence-flagged fields. |
| **Price recommendation** | Transparent statistics: recent modal price / robust median / weighted market comparison over cleaned Agmarknet data. **Not** a black-box model — by design, so it's explainable to judges. Adjustments (quality/season/transport) explicit & configurable. |
| **Demand forecasting** | Seasonal-naive baseline → LightGBM comparison when history suffices. Stores model version, training window, metrics, timestamps. Marked synthetic in demo. |
| **Image quality** | MVP: validation, compression, storage + manual grading workflow. Classification/defects only if a real compatible model exists — **never invented accuracy numbers**. |
| **Route optimisation** | Real: Google OR-Tools VRP with capacity/time-window constraints; OSRM for road distances; nearest-neighbour fallback. Never claim "globally optimal". |

---

## 6. External services — verified status (checked 2026-10-25)

| Service | Status | How we get it |
|---|---|---|
| **Agmarknet mandi prices** | ✅ REAL, free | Register at **data.gov.in** → free API key → resource `9ef84268-d588-465a-a308-a864a43d0070` ("Current Daily Price of Various Commodities from Various Markets"). Filters: state/district/market/commodity. Unofficial keyless mirror exists (mandi-api.vercel.app) for prototyping only. |
| **Bhashini ASR/TTS** | ✅ REAL, free | Register on **bhashini.gov.in / ULCA portal** → API key → official `bhashini-client-sdk` (Python). ASR + translation + TTS, ~22 languages incl. Telugu. Model IDs specified per request. |
| **AI4Bharat models** | ✅ REAL, open | `ai4bharat/indic-conformer-600m-multilingual` (all 22 languages) & IndicWhisper on HuggingFace — self-hostable fallback if Bhashini API is down. GPU helps here (600M params ≈ ~2.4 GB VRAM — fits any T4). |
| **OSRM routing** | ✅ FREE (demo-grade) | `router.project-osrm.org` — free, no key, but officially "demo only", shared ~5,000 req/min, small distance-matrix limits. Fine for SIH demo; self-host via Docker (`osrm/osrm-backend` + India `.osm.pbf` extract) if we need bigger matrices. |
| **IMD weather** | ⚠️ REAL but fiddly | **api.imd.gov.in** — register → dev API key; requires server **IP binding** (annoying on laptops). Fallback: Open-Meteo (free, no key) for the demo; label the source honestly. |
| **Payment aggregator** | 🔶 Sandbox only for MVP | Razorpay-style provider in **test mode** behind our payment adapter, or the clearly-labelled simulated sandbox. Real escrow/split settlement = post-hackathon, provider-approved. |
| **SMS/voice** | 🔶 Adapter + simulation | Real adapters are simple to add later; MVP = in-app notifications + simulated SMS/voice logs behind the same interface. |
| **ONDC** | ⛔ Future extension only | Spec explicitly says: don't pretend to be ONDC-certified. |

**Architectural key:** every external provider sits behind an **adapter interface** with a mock implementation — same interface for demo and production. Demo mode is explicit (`DEMO_MODE` config), and all demo data is labelled synthetic.

---

## 7. GPU / Kaggle — the honest verdict

**The MVP does NOT need GPU.** Here's why:

| Workload | GPU needed? | Why |
|---|---|---|
| Price recommendation | ❌ No | Median/modal-price statistics on tabular rows — CPU, milliseconds |
| Demand forecasting (LightGBM/sklearn) | ❌ No | Agmarknet tabular history — trains in seconds/minutes on CPU |
| Speech recognition | ❌ No (via API) | Bhashini does the inference in their cloud; we just call the API |
| Route optimisation (OR-Tools) | ❌ No | CPU combinatorial solver |
| Image validation/compression | ❌ No | Pillow/OpenCV basics |

**Where Kaggle GPU (T4×2 / P100, ~30 GPU-hrs/week) WOULD genuinely help — as optional stretch goals:**

1. **Self-hosted ASR fallback** — run & evaluate IndicConformer locally so the demo survives a Bhashini outage (nice robustness story for judges).
2. **Fine-tune Whisper-small on Telugu agricultural vocabulary** (crop names, units like క్వింటాల్, mandi terms) — a real differentiator if time permits; Whisper-small fine-tunes comfortably in a Kaggle T4 session.
3. **Image defect-classification experiments** — only if we decide to go beyond manual grading.

**How we'd use it when the time comes:** I write the notebook; you either run it in your Kaggle account, or drop a `kaggle.json` API token (Settings → Create New Token) into the project so I can push and launch kernels via the Kaggle CLI. **Never share your Kaggle password** — the token is the safe path and can be regenerated/revoked anytime. We're not there yet; nothing to do now.

---

## 8. Scope reality check — the smart SIH cut

The full spec, quantified:

- **87 screens** (10 public + 19 farmer + 19 buyer + 13 driver + 12 FPO + 14 admin)
- **43 database tables**
- **27 API route groups**
- 6 roles, 6 workflows, 7 phases, 25-item Definition of Done

That's a 3–6 month product build compressed into spec form. **Nobody should attempt 100% of it before SIH.** The winning strategy:

### Must-have (the judge demo depends on it) — build first
- Auth with roles + demo login · farmer listing (manual + voice-simulated first, real Bhashini next) · price recommendation with visible source/date · buyer browse/cart/order · farmer accept/reject + inventory reservation · simulated payment with ledger · FPO aggregation → shipment → OR-Tools route · driver stops + QR confirm · order state machine + timeline · admin dashboard reading **real DB values** · seed/reset demo data · English + Telugu strings.

### Strong-second (differentiators, add once the loop works)
- Real Bhashini ASR integration · real Agmarknet importer + data-quality flags · demand forecast chart (labelled synthetic/baseline) · earnings & settlement views · grievances · notifications centre · weekly basket · business RFQ (simplified).

### Demo-day optional / explicitly deferred
- Business recurring orders, consolidated invoices · image quality ML · ONDC · real SMS/IVR · real payment provider (keep sandbox) · PostGIS geo queries (plain lat/long + haversine is enough for the demo) · Prophet comparison.

**Vertical slice first** (spec's own advice): farmer listing → buyer order → accept → delivery → settlement working end-to-end beats twenty polished screens that go nowhere.

---

## 9. Build order (spec's 7 phases, made concrete)

| Phase | Deliverable | "Done" looks like |
|---|---|---|
| 0. Init | Repo, folder structure, design tokens | `git init`, Flutter + FastAPI skeletons, `.env.example` |
| 1. Foundation | Auth, roles, DB schema, migrations | Demo users sign in; role-based nav; 43-table schema migrated |
| 2. Marketplace | Listings → cart → orders → acceptance | **The vertical slice demo runs on one shared DB** |
| 3. Pricing & voice | Agmarknet importer, cleaning, recommendations, voice adapter, forecast baseline | Recommendation shows real mandi price + date + source; voice flow has manual fallback |
| 4. Logistics | FPO intake, shipment, OR-Tools route, QR gen/verify | Driver completes a QR-verified delivery |
| 5. Payments & notifications | Sandbox checkout, webhook handling (simulated), ledger, settlements, notification centre | Every rupee traceable in ledger; order & payment status consistent |
| 6. Admin | Verifications, dashboards, audit log, analytics, demo-data controls | Admin sees the entire demo transaction trail |
| 7. Hardening | Tests (unit/integration/e2e incl. one invalid path), Docker, docs, APK build | Definition-of-Done checklist passes honestly |

---

## 10. The 15-step demo script (what judges actually see)

1. Sign in as farmer → 2. create listing (voice sim or manual) → 3. view price recommendation + source/date → 4. sign in as buyer → 5. browse & order → 6. accept as farmer → 7. simulated payment → 8. sign in as FPO → 9. aggregate & create shipment → 10. assign driver + optimise route → 11. sign in as driver → 12. QR pickup & delivery confirm → 13. order completes → 14. inspect payment/settlement records → 15. view the whole transaction in admin.

All roles on **one shared backend and database** — that's the whole point.

---

## 11. Spec red lines (violating these = credibility loss with judges)

- ❌ Never mark a payment successful because a button was clicked — webhook/reconciliation only
- ❌ Never hold customer money in a normal account / call ordinary authorisation "escrow"
- ❌ Never invent AI accuracy metrics, training data, or field-validation results
- ❌ Never present stale/synthetic prices as current official mandi prices
- ❌ Never auto-publish low-confidence speech results; never guess missing qty/price
- ❌ Never claim the app works on basic feature phones without a real IVR/USSD/SMS service
- ❌ Never charge farmers an undisclosed commission; deductions must be configured & visible
- ❌ Never claim regulatory compliance just because security features exist
- ❌ Never use floats for money — integer paise
- ❌ Dev OTPs/demo logins must be impossible in production mode

---

## 12. Money flow (per the spec's proposed — configurable — rules)

- **Farmers pay nothing.**
- Buyer pays: produce subtotal + delivery fee + ~2–3% platform fee (configurable).
- On delivery confirmation, settlement splits visibly: **farmer gross proceeds → (any authorised deductions) → net payout**; driver compensation; platform fee — all as double-entry-style ledger entries with idempotency guards.
- Every screen that shows a farmer rupee figure must show gross, deductions, and net.

---

## 13. Repository layout (when we start building)

```
sih/
├── app/                    # Flutter (Android-first + web)
│   └── lib/{app,core,features/*,l10n}
├── backend/                # FastAPI
│   └── app/{core,api/v1,models,schemas,services,integrations/*,ai/*,tasks,db}
├── docs/                   # architecture, ERD, sequence diagrams, demo guide
├── docker-compose.yml      # postgres + redis + backend + (optional osrm)
├── .env.example            # placeholders only
└── ANALYSIS.md             # ← this file
```

---

## 14. What I need from you (nothing blocking; all optional)

| Item | Why | Urgency |
|---|---|---|
| data.gov.in API key (free signup) | Real mandi prices | Before Phase 3 |
| Bhashini/ULCA account + key (free) | Real Telugu/Hindi voice listing | Before Phase 3 |
| Kaggle `kaggle.json` token (or you run my notebook) | Only if we do the GPU stretch goals (ASR fallback / Whisper fine-tune) | Weeks away, if at all |
| Team deadline date | To calibrate the scope cut | Helpful now |

Everything else — Docker, OSRM demo server, Open-Meteo, payment sandbox — needs no credentials to start.

---

## 15. Bottom line

The spec is unusually well-written and honest: it's an **anti-fake-news engineering brief**. The path to a strong SIH showing is not building all 87 screens — it's one **bulletproof, fully-traceable vertical slice** (voice → listing → order → shared delivery → QR → payment ledger → admin audit), dressed in a clean KhetSe-branded Flutter UI, backed by **real Agmarknet price data and real Bhashini voice**, with every simulated part **visibly labelled**. GPU isn't needed for that core; Kaggle stays in reserve for optional speech-model stretch goals.
