"""MOCK speech provider: clearly-labelled simulation for demo mode.

There is no offline ASR engine bundled with KhetSe, so without Bhashini
credentials the platform does not pretend to recognise speech. The mock:

- relays typed ``text`` as the "transcript" (the demo user is the speaker);
- carries ``provider="mock"`` and ``simulated=True`` on every result, and the
  API surfaces both fields so the client can badge the output as simulated;
- NEVER accepts audio: the router intercepts audio while the mock is active
  and answers 422 with instructions to type text instead, so a demo can never
  fabricate a transcript that did not exist.
"""

from app.integrations.speech.base import TranscriptionResult


class MockSpeechAdapter:
    """Simulated provider — the honest fallback when no real ASR is wired."""

    name = "mock"
    simulated = True

    def transcribe(self, audio_base64: str, language: str) -> TranscriptionResult:
        # The mock has no speech engine. Reaching this method means the caller
        # bypassed the router's demo-mode audio guard — fail loudly rather
        # than invent a transcript.
        raise NotImplementedError(
            "Mock speech provider cannot transcribe audio; send typed text "
            "instead (simulated demo mode)."
        )

    def simulate_text(self, text: str, language: str) -> TranscriptionResult:
        """Wrap typed demo text as a labelled transcription result."""
        return TranscriptionResult(
            transcript=(text or "").strip(),
            confidence=1.0,
            provider=self.name,
            simulated=self.simulated,
        )
