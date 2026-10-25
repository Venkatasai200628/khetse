"""Voice listing-draft (simulated ASR) and business-buyer RFQ flow tests.

Voice: provider status is mock/simulated by default, typed text drafts are
parsed for quantity/unit/price/date/commodity (English AND Telugu), audio is
rejected with a clear 422 while the simulation is active, and missing fields
are surfaced for confirmation — never guessed.

RFQ: business → open RFQ → farmer quote (from their own active listing) →
buyer accept ⇒ one atomic transaction that reserves the listing, opens an
order in payment_pending and closes the request. Ownership, role and
double-accept guards are covered.
"""

import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import httpx
import pytest

from app.ai.extraction import parser
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.integrations.speech import base as speech_base
from app.integrations.speech import bhashini as bhashini_module
from app.main import app
from tests.helpers import register_user, seed_commodity

import app.api.v1.rfq as rfq_api
import app.api.v1.voice as voice_api

# The voice/rfq routers are registered centrally in app/api/v1/__init__.py,
# which is owned by another work stream. Keep this suite self-sufficient
# either way: include them here if and only if they are not wired up yet.
_REGISTERED_PATHS = {getattr(route, "path", "") for route in app.routes}
if "/api/v1/voice/status" not in _REGISTERED_PATHS:
    app.include_router(voice_api.router, prefix="/api/v1")
if "/api/v1/rfq/mine" not in _REGISTERED_PATHS:
    app.include_router(rfq_api.router, prefix="/api/v1")


# --- Shared fixtures ------------------------------------------------------------


@pytest.fixture()
def tomato_id():
    return seed_commodity()


@pytest.fixture()
def farmer(client):
    return register_user(client, "+919800000101", "Ramu Farmer", "farmer")


@pytest.fixture()
def business(client):
    return register_user(client, "+919800000102", "Big Bazaar", "business")


def _create_listing(client, farmer_headers, commodity_id, qty=100.0, price=2200):
    r = client.post(
        "/api/v1/listings",
        headers=farmer_headers,
        json={
            "commodity_id": commodity_id,
            "quantity_total": qty,
            "unit": "kg",
            "min_price_paise": 1800,
            "listed_price_paise": price,
            "quality_grade": "A",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _open_rfq(client, business_headers, commodity_id, **overrides):
    payload = {
        "commodity_id": commodity_id,
        "quantity": 50,
        "unit": "kg",
        "needed_by": "2026-11-30",
        "district": "Kurnool",
        "max_price_paise": 2500,
        "notes": "Weekly bulk supply for our store",
    }
    payload.update(overrides)
    r = client.post("/api/v1/rfq", headers=business_headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _quote(client, farmer_headers, request_id, listing_id, **overrides):
    payload = {
        "listing_id": listing_id,
        "quantity": 50,
        "unit": "kg",
        "price_paise": 2200,
        "message": "Fresh harvest, can deliver weekly",
        "valid_until": "2026-12-01T00:00:00Z",
    }
    payload.update(overrides)
    r = client.post(
        f"/api/v1/rfq/{request_id}/offers", headers=farmer_headers, json=payload
    )
    return r


def _user_id_by_phone(phone: str) -> str:
    from sqlalchemy import select

    from app.models.user import User

    db = SessionLocal()
    try:
        return str(db.scalar(select(User.id).where(User.phone == phone)))
    finally:
        db.close()


# --- Voice: provider status -------------------------------------------------------


def test_voice_status_reports_mock_provider_by_default(client, business):
    # No BHASHINI_API_KEY configured → clearly-labelled simulated provider.
    r = client.get("/api/v1/voice/status", headers=business["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "mock"
    assert body["simulated"] is True
    assert body["languages_supported"] == ["en", "te", "hi"]


def test_voice_status_reports_bhashini_when_key_configured(client, business, monkeypatch):
    class _BhashiniStub:
        name = "bhashini"
        simulated = False

    monkeypatch.setattr(voice_api, "get_speech_adapter", lambda: _BhashiniStub())
    r = client.get("/api/v1/voice/status", headers=business["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "bhashini"
    assert body["simulated"] is False


def test_voice_status_requires_authentication(client):
    r = client.get("/api/v1/voice/status")
    assert r.status_code == 401


# --- Voice: adapter resolution (unit) ----------------------------------------------


def test_speech_provider_resolution_follows_api_key():
    assert speech_base.resolve_speech_provider(Settings()) == "mock"
    configured = Settings(BHASHINI_API_KEY="secret-key", BHASHINI_USER_ID="user-1")
    assert speech_base.resolve_speech_provider(configured) == "bhashini"
    adapter = speech_base.get_speech_adapter(configured)
    assert adapter.name == "bhashini" and adapter.simulated is False
    mock_adapter = speech_base.get_speech_adapter(Settings())
    assert mock_adapter.name == "mock" and mock_adapter.simulated is True


def test_bhashini_adapter_raises_app_error_on_provider_failure(monkeypatch):
    class _FailingClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(bhashini_module.httpx, "Client", _FailingClient)
    adapter = bhashini_module.BhashiniASRAdapter(
        api_key="test-key", user_id="test-user"
    )
    with pytest.raises(AppError, match="Bhashini ASR failed"):
        adapter.transcribe("UklGRg==", "te")


# --- Voice: listing draft ------------------------------------------------------------


def test_listing_draft_english_text(client, farmer, tomato_id):
    r = client.post(
        "/api/v1/voice/listing-draft",
        headers=farmer["headers"],
        json={"text": "10 kg tomato at 20 rupees per kg", "language": "en"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["transcript"] == "10 kg tomato at 20 rupees per kg"
    assert body["provider"] == "mock"
    assert body["simulated"] is True
    assert body["detected_language"] == "en"

    extracted = body["extracted"]
    assert extracted["commodity"]["id"] == tomato_id
    assert extracted["commodity"]["name_en"] == "Tomato"
    assert extracted["commodity"]["confidence"] == 1.0
    assert extracted["quantity"] == 10.0
    assert extracted["unit"] == "kg"
    assert extracted["price_paise"] == 2000  # ₹20/kg → integer paise

    # Only the availability date was not said — everything else is certain.
    assert body["fields_needing_confirmation"] == ["available_from"]
    assert body["confidence"] == 1.0


def test_listing_draft_telugu_text(client, farmer, tomato_id):
    r = client.post(
        "/api/v1/voice/listing-draft",
        headers=farmer["headers"],
        json={"text": "5 క్వింటాల్ టమాటా రూ 2000", "language": "te"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["detected_language"] == "te"
    assert body["simulated"] is True

    extracted = body["extracted"]
    assert extracted["commodity"]["name_en"] == "Tomato"  # via టమాటా
    assert extracted["quantity"] == 5.0
    assert extracted["unit"] == "quintal"  # క్వింటాల్
    assert extracted["price_paise"] == 200_000  # రూ 2000 → paise
    assert "available_from" in body["fields_needing_confirmation"]


def test_listing_draft_rejects_audio_in_demo_mode(client, farmer):
    r = client.post(
        "/api/v1/voice/listing-draft",
        headers=farmer["headers"],
        json={"audio_base64": "UklGRg==", "language": "te"},
    )
    assert r.status_code == 422
    assert "Speech simulation is active" in r.json()["error"]["message"]


def test_listing_draft_lists_missing_fields_for_confirmation(client, farmer, tomato_id):
    r = client.post(
        "/api/v1/voice/listing-draft",
        headers=farmer["headers"],
        json={"text": "tomato", "language": "en"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    extracted = body["extracted"]
    assert extracted["commodity"]["name_en"] == "Tomato"
    assert extracted["quantity"] is None
    assert extracted["unit"] is None
    assert extracted["price_paise"] is None
    assert body["fields_needing_confirmation"] == [
        "quantity",
        "unit",
        "price",
        "available_from",
    ]


def test_listing_draft_requires_farmer_role(client, business):
    r = client.post(
        "/api/v1/voice/listing-draft",
        headers=business["headers"],
        json={"text": "10 kg tomato", "language": "en"},
    )
    assert r.status_code == 403


# --- Parser (pure-function units) ---------------------------------------------------


def _catalogue():
    return [
        SimpleNamespace(
            id=uuid.uuid4(), name_en="Tomato", name_te="టమాటా", name_hi="टमाटर"
        ),
        SimpleNamespace(
            id=uuid.uuid4(), name_en="Onion", name_te="ఉల్లి", name_hi="प्याज"
        ),
    ]


def test_parser_quantity_units_and_prices():
    fields = parser.extract_listing_fields(
        "10 kg tomato at 20 rupees per kg", _catalogue()
    )
    assert (fields["quantity"], fields["unit"], fields["price_paise"]) == (
        10.0,
        "kg",
        2000,
    )

    # Decimal quantity, ₹ prefix, plural unit.
    fields = parser.extract_listing_fields("2.5 quintals onion ₹3100", _catalogue())
    assert (fields["quantity"], fields["unit"], fields["price_paise"]) == (
        2.5,
        "quintal",
        310_000,
    )

    # Telugu units, including the mixed-script plural "kgల" and డజను.
    fields = parser.extract_listing_fields("20 kgల ఉల్లి రూ 15", _catalogue())
    assert (fields["quantity"], fields["unit"]) == (20.0, "kg")
    assert fields["price_paise"] == 1500
    fields = parser.extract_listing_fields("3 డజను టమాటా", _catalogue())
    assert (fields["quantity"], fields["unit"]) == (3.0, "dozen")


def test_parser_handles_indic_digits():
    # Telugu digit ౫ and Devanagari ५ both mean 5.
    fields = parser.extract_listing_fields("౫ క్వింటాల్ టమాటా రూ 2000", _catalogue())
    assert fields["quantity"] == 5.0
    assert fields["unit"] == "quintal"
    fields = parser.extract_listing_fields("౫ టన్ను టమాటా", _catalogue())
    assert fields["quantity"] == 5.0
    assert fields["unit"] == "tonne"
    fields = parser.extract_listing_fields("५ kg टमाटर", _catalogue())
    assert fields["quantity"] == 5.0
    assert fields["unit"] == "kg"


def test_parser_relative_dates():
    today = date(2026, 10, 25)
    cases = {
        "tomato ready today": today,
        "టమాటా ఈరోజు": today,
        "tomato రేపు": today + timedelta(days=1),
        "tomato day after tomorrow": today + timedelta(days=2),
        "tomato ఎల్లుడు": today + timedelta(days=2),
        "tomato 10 kg": None,  # no date mentioned → never guessed
    }
    for text, expected in cases.items():
        assert parser.extract_available_from(text, today=today) == expected, text


def test_parser_commodity_matching_with_synonyms():
    catalogue = _catalogue()
    assert parser.match_commodity("fresh tamata stock", catalogue)["name_en"] == "Tomato"
    assert parser.match_commodity("10 kg ulli", catalogue)["name_en"] == "Onion"
    assert parser.match_commodity("ఉల్లి రూ 20", catalogue)["name_en"] == "Onion"
    # No catalogue row for mangoes → no match, never invented.
    assert parser.match_commodity("10 kg mango", catalogue) is None


def test_parser_never_guesses_missing_values():
    fields = parser.extract_listing_fields("good quality fresh stock", _catalogue())
    assert fields["commodity"] is None
    assert fields["quantity"] is None
    assert fields["unit"] is None
    assert fields["price_paise"] is None
    assert fields["available_from"] is None
    assert fields["confidence"] == 0.0
    # A bare number with no unit/currency context is not a quantity or price.
    fields = parser.extract_listing_fields("stock 40", _catalogue())
    assert fields["quantity"] is None
    assert fields["price_paise"] is None


# --- RFQ: full flow ------------------------------------------------------------------


def test_full_rfq_flow_to_payment_pending(client, farmer, business, tomato_id):
    listing = _create_listing(client, farmer["headers"], tomato_id)

    # Business opens the RFQ.
    rfq = _open_rfq(client, business["headers"], tomato_id)
    assert rfq["status"] == "open"
    assert rfq["commodity_name"] == "Tomato"
    assert rfq["business_user_id"] == _user_id_by_phone("+919800000102")
    assert rfq["offers"] == []

    # Farmer discovers it among open requests.
    r = client.get("/api/v1/rfq/open", headers=farmer["headers"])
    assert r.status_code == 200, r.text
    open_ids = [row["id"] for row in r.json()]
    assert rfq["id"] in open_ids

    # Farmer quotes from their own active listing.
    r = _quote(client, farmer["headers"], rfq["id"], listing["id"])
    assert r.status_code == 201, r.text
    offer = r.json()
    assert offer["status"] == "pending"
    assert offer["farmer_name"] == "Ramu Farmer"
    assert offer["line_total_paise"] == 50 * 2200

    # Buyer sees the quote on their request (mine + comparison endpoint).
    r = client.get("/api/v1/rfq/mine", headers=business["headers"])
    assert r.status_code == 200, r.text
    mine = r.json()
    assert len(mine) == 1 and mine[0]["id"] == rfq["id"]
    assert len(mine[0]["offers"]) == 1
    r = client.get(f"/api/v1/rfq/{rfq['id']}/offers", headers=business["headers"])
    assert r.status_code == 200, r.text
    offers = r.json()
    assert len(offers) == 1
    assert offers[0]["price_paise"] == 2200
    assert offers[0]["farmer_name"] == "Ramu Farmer"
    assert offers[0]["valid_until"] is not None

    # Buyer accepts → one order, payment_pending, listing quantity reserved.
    r = client.post(
        f"/api/v1/rfq/offers/{offer['id']}/accept", headers=business["headers"]
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["offer"]["status"] == "accepted"
    assert body["offer"]["responded_at"] is not None
    order = body["order"]
    assert order["status"] == "payment_pending"
    assert order["payment_status"] == "pending"
    assert order["buyer_id"] == _user_id_by_phone("+919800000102")
    assert order["subtotal_paise"] == 110_000  # 50 kg × ₹22
    assert order["delivery_fee_paise"] == 3_000
    assert order["platform_fee_paise"] == 2_750  # 2.5%
    assert order["total_paise"] == 115_750
    assert order["items"][0]["listing_id"] == listing["id"]
    assert order["items"][0]["farmer_id"] == _user_id_by_phone("+919800000101")
    assert order["items"][0]["quantity"] == 50
    assert order["items"][0]["unit_price_paise"] == 2200
    assert order["items"][0]["farmer_response"] == "accepted"

    # Inventory: 100 kg listed, 50 kg accepted → 50 available.
    r = client.get(f"/api/v1/listings/{listing['id']}", headers=farmer["headers"])
    assert r.json()["quantity_available"] == 50

    # Purchase request is closed after acceptance.
    r = client.get("/api/v1/rfq/mine", headers=business["headers"])
    assert r.json()[0]["status"] == "closed"

    # The state machine recorded every system step of the accepted path.
    events = [e["to_status"] for e in order["status_events"]]
    assert events == [
        "awaiting_farmer_confirmation",
        "accepted",
        "payment_pending",
    ]


def test_farmer_cannot_create_rfq(client, farmer, tomato_id):
    r = client.post(
        "/api/v1/rfq",
        headers=farmer["headers"],
        json={"commodity_id": tomato_id, "quantity": 10, "unit": "kg"},
    )
    assert r.status_code == 403


def test_accept_offer_requires_the_request_owner(
    client, farmer, business, tomato_id
):
    listing = _create_listing(client, farmer["headers"], tomato_id)
    rfq = _open_rfq(client, business["headers"], tomato_id)
    offer = _quote(client, farmer["headers"], rfq["id"], listing["id"]).json()

    other_business = register_user(client, "+919800000103", "Other Mart", "business")
    r = client.post(
        f"/api/v1/rfq/offers/{offer['id']}/accept",
        headers=other_business["headers"],
    )
    assert r.status_code == 403

    # And the offers of someone else's request are not visible either.
    r = client.get(f"/api/v1/rfq/{rfq['id']}/offers", headers=other_business["headers"])
    assert r.status_code == 403

    # Farmers cannot accept their own offers (business-only action).
    r = client.post(
        f"/api/v1/rfq/offers/{offer['id']}/accept", headers=farmer["headers"]
    )
    assert r.status_code == 403


def test_double_accept_conflicts(client, farmer, business, tomato_id):
    listing = _create_listing(client, farmer["headers"], tomato_id)
    rfq = _open_rfq(client, business["headers"], tomato_id)
    offer = _quote(client, farmer["headers"], rfq["id"], listing["id"]).json()

    first = client.post(
        f"/api/v1/rfq/offers/{offer['id']}/accept", headers=business["headers"]
    )
    assert first.status_code == 200, first.text

    second = client.post(
        f"/api/v1/rfq/offers/{offer['id']}/accept", headers=business["headers"]
    )
    assert second.status_code == 409
    assert "already been accepted" in second.json()["error"]["message"]

    # Idempotency at the data level: exactly one order exists for the offer.
    from sqlalchemy import select

    from app.models.commerce import Order

    db = SessionLocal()
    try:
        count = len(
            db.scalars(
                select(Order).where(
                    Order.idempotency_key == f"rfq-offer-{offer['id']}"
                )
            ).all()
        )
        assert count == 1
    finally:
        db.close()


def test_offer_validations(client, farmer, business, tomato_id):
    listing = _create_listing(client, farmer["headers"], tomato_id, qty=10)

    other_farmer = register_user(client, "+919800000104", "Lata Farmer", "farmer")
    other_listing = _create_listing(client, other_farmer["headers"], tomato_id)

    rfq = _open_rfq(client, business["headers"], tomato_id)

    # Can only quote from your OWN listings.
    r = _quote(client, other_farmer["headers"], rfq["id"], listing["id"])
    assert r.status_code == 403

    # Oversupplying beyond the listing's available quantity is rejected.
    r = _quote(
        client, farmer["headers"], rfq["id"], listing["id"], quantity=11
    )
    assert r.status_code == 409

    # A paused (non-active) listing cannot be quoted, even by its owner.
    r = client.patch(
        f"/api/v1/listings/{other_listing['id']}/status",
        headers=other_farmer["headers"],
        json={"status": "paused"},
    )
    assert r.status_code == 200, r.text
    r = _quote(client, other_farmer["headers"], rfq["id"], other_listing["id"])
    assert r.status_code == 409

    # Unknown request → 404.
    r = _quote(client, farmer["headers"], uuid.uuid4(), listing["id"])
    assert r.status_code == 404

    # After acceptance the request is closed → further quotes are 409.
    offer = _quote(
        client, farmer["headers"], rfq["id"], listing["id"], quantity=5
    ).json()
    r = client.post(
        f"/api/v1/rfq/offers/{offer['id']}/accept", headers=business["headers"]
    )
    assert r.status_code == 200, r.text
    r = _quote(client, farmer["headers"], rfq["id"], listing["id"], quantity=1)
    assert r.status_code == 409
