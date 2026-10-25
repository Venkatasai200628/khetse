"""Speech-to-text adapters: one interface, two providers.

- :class:`app.integrations.speech.bhashini.BhashiniASRAdapter` — REAL adapter
  for the Bhashini (ULCA) ASR pipeline, used only when ``BHASHINI_API_KEY``
  is configured.
- :class:`app.integrations.speech.mock.MockSpeechAdapter` — clearly-labelled
  simulated fallback used in demo mode: it cannot hear audio at all and only
  relays typed text, and every response it produces is tagged
  ``provider="mock"`` / ``simulated=True`` so a demo transcript can never be
  mistaken for a real recognition result.
"""

from app.integrations.speech.base import (
    SUPPORTED_LANGUAGES,
    TranscriptionResult,
    get_speech_adapter,
)

__all__ = ["SUPPORTED_LANGUAGES", "TranscriptionResult", "get_speech_adapter"]
