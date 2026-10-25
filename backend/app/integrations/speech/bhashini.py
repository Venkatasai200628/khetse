"""REAL speech provider: Bhashini ASR through the ULCA inference pipeline.

Implements the standard two-step ULCA ASR flow against the MeitY/Bhashini
gateway (https://bhashini.gov.in — register on the ULCA portal for a key):

1. **Model search** — ``POST {ULCA_MODEL_SEARCH_URL}`` with the ``userID`` and
   ``ulcaApiKey`` headers asks the gateway for an ASR pipeline for the source
   language. The reply carries the inference endpoint, its auth header
   name/value and the concrete ASR ``serviceId``.
2. **Inference** — ``POST`` the base64 audio to the returned ``inferenceUrl``
   using the returned auth header; the reply's
   ``pipelineResponse[0].output[0].transcript`` is the recognised text.

Credentials come from settings (``BHASHINI_API_KEY`` / ``BHASHINI_USER_ID``).
Every failure path — timeout, HTTP error, unexpected payload, empty
transcript — raises ``AppError("Bhashini ASR failed: …")``. The adapter NEVER
fabricates a transcript and never silently falls back to the mock: callers
get either a real recognition result or a loud failure.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import status

from app.core.config import get_settings
from app.core.errors import AppError
from app.integrations.speech.base import TranscriptionResult

logger = logging.getLogger("khetse.speech")

# ULCA gateway endpoints (public MeitY API space of the Bhashini platform).
ULCA_MODEL_SEARCH_URL = (
    "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
)
# Documented MeitY ASR pipeline id (ULCA docs / Bhashini onboarding pack).
ULCA_ASR_PIPELINE_ID = "64392f96daac500b55c543cd"

# Some deployments answer the model search with a placeholder auth value
# ("~") that means "reuse the ulcaApiKey for inference".
_PLACEHOLDER_AUTH_VALUES = frozenset({"~", "#"})

# Wall-clock budget for EACH of the two HTTP calls.
DEFAULT_TIMEOUT_SECONDS = 15.0


class BhashiniASRAdapter:
    """REAL adapter for the Bhashini (ULCA) automatic speech recognition."""

    name = "bhashini"
    simulated = False

    def __init__(
        self,
        api_key: str | None = None,
        user_id: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        model_search_url: str = ULCA_MODEL_SEARCH_URL,
    ):
        settings = get_settings()
        self.api_key = (api_key or settings.BHASHINI_API_KEY).strip()
        self.user_id = (user_id or settings.BHASHINI_USER_ID).strip()
        self.timeout = timeout
        self.model_search_url = model_search_url

    # --- ULCA pipeline steps --------------------------------------------------

    def _search_pipeline(self, client: httpx.Client, language: str) -> dict:
        """Step 1: ask the gateway for an ASR pipeline for `language`."""
        try:
            response = client.post(
                self.model_search_url,
                headers={
                    "userID": self.user_id,
                    "ulcaApiKey": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "pipelineTasks": [
                        {
                            "taskType": "asr",
                            "config": {"language": {"sourceLanguage": language}},
                        }
                    ],
                    "pipelineRequestConfig": {"pipelineId": ULCA_ASR_PIPELINE_ID},
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise self._failed(f"model search unreachable ({type(exc).__name__})") from exc
        except ValueError as exc:  # non-JSON body
            raise self._failed("model search returned a non-JSON body") from exc

    @staticmethod
    def _failed(detail: str) -> AppError:
        # 502: the caller's request was fine — the upstream provider failed.
        return AppError(
            f"Bhashini ASR failed: {detail}",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    @staticmethod
    def _extract_inference_target(search_body: dict) -> tuple[str, str, str, str]:
        """Pull (inference_url, auth_header_name, auth_header_value, service_id)."""
        try:
            endpoint = search_body["pipelineInferenceAPIEndPoint"]
            inference_url = endpoint["inferenceUrl"]
            auth = endpoint["inferenceApiKey"]
            auth_name = auth["name"]
            auth_value = auth["value"]
            service_id = search_body["pipelineResponseConfig"][0]["config"][0][
                "serviceId"
            ]
        except (KeyError, IndexError, TypeError) as exc:
            raise BhashiniASRAdapter._failed(
                "unexpected model-search response shape"
            ) from exc
        return inference_url, auth_name, auth_value, service_id

    def transcribe(self, audio_base64: str, language: str) -> TranscriptionResult:
        """Transcribe base64 audio; raise ``AppError`` on any failure."""
        if not audio_base64:
            raise self._failed("no audio content provided")
        if not self.api_key or not self.user_id:
            raise self._failed("BHASHINI_API_KEY / BHASHINI_USER_ID not configured")

        with httpx.Client(timeout=httpx.Timeout(self.timeout, connect=10.0)) as client:
            search_body = self._search_pipeline(client, language)
            inference_url, auth_name, auth_value, service_id = (
                self._extract_inference_target(search_body)
            )
            if auth_value in _PLACEHOLDER_AUTH_VALUES:
                auth_value = self.api_key

            try:
                response = client.post(
                    inference_url,
                    headers={auth_name: auth_value, "Content-Type": "application/json"},
                    json={
                        "pipelineTasks": [
                            {
                                "taskType": "asr",
                                "config": {
                                    "language": {
                                        "sourceLanguage": language,
                                        "sourceScriptCode": "",
                                    },
                                    "serviceId": service_id,
                                    "audioFormat": "wav",
                                },
                            }
                        ],
                        "inputData": {
                            "audio": [{"audioContent": audio_base64}],
                        },
                    },
                )
                response.raise_for_status()
                inference_body = response.json()
            except httpx.HTTPError as exc:
                raise self._failed(
                    f"inference call failed ({type(exc).__name__})"
                ) from exc
            except ValueError as exc:
                raise self._failed("inference returned a non-JSON body") from exc

        try:
            output = inference_body["pipelineResponse"][0]["output"][0]
        except (KeyError, IndexError, TypeError) as exc:
            raise self._failed("unexpected inference response shape") from exc

        transcript = str(output.get("transcript") or "").strip()
        if not transcript:
            # Never fabricate: an empty recognition result is an error, not "".
            raise self._failed("empty transcript returned")

        try:
            confidence = float(output.get("confidence") or 1.0)
        except (TypeError, ValueError):
            confidence = 1.0
        return TranscriptionResult(
            transcript=transcript,
            confidence=max(0.0, min(1.0, confidence)),
            provider=self.name,
            simulated=self.simulated,
        )
