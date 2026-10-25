"""Voice endpoints: provider status and the voice-driven listing draft.

`GET /voice/status` tells the client which speech provider is active and
whether output is SIMULATED — the demo UI must badge simulated drafts.

`POST /voice/listing-draft` turns a farmer's spoken/typed utterance into a
structured draft. With the real Bhashini provider the audio is transcribed by
ASR; with the mock provider (no credentials — the default) audio is rejected
with a clear 422 and typed text is used instead, always labelled
``provider="mock", simulated=true``. Extraction never guesses: anything the
parser could not find is listed in ``fields_needing_confirmation`` for the
farmer to fill in, never invented.
"""

import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.extraction import parser
from app.core.deps import get_current_user, require_roles
from app.core.errors import ValidationAppError
from app.db.session import get_db
from app.integrations.speech import SUPPORTED_LANGUAGES, get_speech_adapter
from app.models.catalog import Commodity
from app.models.enums import RoleEnum
from app.models.user import User

router = APIRouter(prefix="/voice", tags=["voice"])

DEMO_MODE_AUDIO_MESSAGE = (
    "Speech simulation is active: send text instead of audio in demo mode."
)


# --- Schemas -------------------------------------------------------------------


class VoiceStatusResponse(BaseModel):
    provider: str
    simulated: bool
    languages_supported: list[str]


class VoiceListingDraftRequest(BaseModel):
    text: str | None = Field(default=None, max_length=2000)
    audio_base64: str | None = Field(default=None, max_length=8_000_000)
    language: Literal["en", "te", "hi"] = "en"

    @model_validator(mode="after")
    def _require_a_source(self) -> "VoiceListingDraftRequest":
        if not (self.text or "").strip() and not self.audio_base64:
            raise ValueError(
                "Provide 'text' (or 'audio_base64' when a real speech provider "
                "is active)."
            )
        return self


class VoiceCommodityMatch(BaseModel):
    id: uuid.UUID
    name_en: str
    confidence: float


class VoiceExtractedDraft(BaseModel):
    commodity: VoiceCommodityMatch | None = None
    quantity: float | None = None
    unit: str | None = None
    price_paise: int | None = None
    available_from: date | None = None


class VoiceListingDraftResponse(BaseModel):
    transcript: str
    detected_language: str
    provider: str
    simulated: bool
    extracted: VoiceExtractedDraft
    fields_needing_confirmation: list[str]
    confidence: float


# --- Endpoints -------------------------------------------------------------------


@router.get("/status", response_model=VoiceStatusResponse)
def voice_status(_user: User = Depends(get_current_user)) -> VoiceStatusResponse:
    """Which speech provider is active, and is its output simulated?"""
    adapter = get_speech_adapter()
    return VoiceStatusResponse(
        provider=adapter.name,
        simulated=adapter.simulated,
        languages_supported=list(SUPPORTED_LANGUAGES),
    )


def _extract_with_catalogue(
    db: Session, transcript: str, today: date
) -> dict[str, Any]:
    commodities = db.scalars(
        select(Commodity).where(Commodity.is_active.is_(True))
    ).all()
    return parser.extract_listing_fields(transcript, commodities, today=today)


@router.post("/listing-draft", response_model=VoiceListingDraftResponse)
def create_listing_draft(
    body: VoiceListingDraftRequest,
    db: Session = Depends(get_db),
    _farmer: User = Depends(require_roles(RoleEnum.FARMER)),
) -> VoiceListingDraftResponse:
    """Turn a spoken/typed utterance into a confirm-before-save listing draft."""
    adapter = get_speech_adapter()

    if adapter.simulated and body.audio_base64:
        # The mock cannot hear — never pretend it can.
        raise ValidationAppError(DEMO_MODE_AUDIO_MESSAGE)

    asr_confidence = 1.0
    transcript = (body.text or "").strip()
    if not transcript and body.audio_base64:
        result = adapter.transcribe(body.audio_base64, body.language)
        transcript = result.transcript.strip()
        asr_confidence = result.confidence

    extraction = _extract_with_catalogue(db, transcript, today=date.today())
    return VoiceListingDraftResponse(
        transcript=transcript,
        detected_language=parser.detect_language(transcript, fallback=body.language),
        provider=adapter.name,
        simulated=adapter.simulated,
        extracted=VoiceExtractedDraft(**{
            key: extraction[key] for key in
            ("commodity", "quantity", "unit", "price_paise", "available_from")
        }),
        fields_needing_confirmation=parser.fields_needing_confirmation(extraction),
        confidence=round(min(asr_confidence, extraction["confidence"]), 2),
    )
