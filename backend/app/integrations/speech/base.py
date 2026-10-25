"""Speech-to-text adapter interface and provider resolution.

Every provider implements :class:`SpeechAdapter`: ``transcribe(audio_base64,
language)`` returns a :class:`TranscriptionResult` whose ``provider`` and
``simulated`` fields travel with the transcript all the way to the client, so
the UI can label simulated output ("demo mode") unambiguously.

Resolution rule (mirrors the other integrations, e.g. market data):
``BHASHINI_API_KEY`` configured → the real Bhashini adapter; otherwise the
clearly-labelled mock. The mock never produces a transcript from audio — the
router rejects audio outright in that case, telling the caller to type text.
"""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings, get_settings

# Languages the voice listing flow supports end to end (ASR + parser).
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "te", "hi")


@dataclass
class TranscriptionResult:
    """Outcome of one speech-to-text call, always fully labelled."""

    transcript: str
    confidence: float
    provider: str
    simulated: bool


class SpeechAdapter(Protocol):
    """The single interface every speech provider implements."""

    name: str
    simulated: bool

    def transcribe(self, audio_base64: str, language: str) -> TranscriptionResult:
        """Transcribe base64-encoded audio in the given language code."""
        ...


def resolve_speech_provider(settings: Settings | None = None) -> str:
    """Name of the active provider for the given settings ("bhashini"|"mock")."""
    settings = settings or get_settings()
    return "bhashini" if settings.BHASHINI_API_KEY.strip() else "mock"


def get_speech_adapter(settings: Settings | None = None) -> SpeechAdapter:
    """Pick the adapter exactly as :func:`resolve_speech_provider` describes."""
    from app.integrations.speech import bhashini, mock

    if resolve_speech_provider(settings) == "bhashini":
        return bhashini.BhashiniASRAdapter()
    return mock.MockSpeechAdapter()
