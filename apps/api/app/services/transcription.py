from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings
from app.schemas.domain import TranscriptResult

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional runtime dependency
    OpenAI = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key and OpenAI is not None else None

    def transcribe_audio(self, audio_path: str | None, transcript_override: str | None = None) -> TranscriptResult:
        print(
            "[TRANSCRIPTION] start",
            {
                "audio_path": audio_path,
                "has_transcript_override": bool(transcript_override),
                "openai_client_available": self.client is not None,
                "transcription_model": settings.openai_transcription_model,
            },
        )
        if transcript_override:
            result = TranscriptResult(transcript=transcript_override.strip(), source="transcript_override")
            print("[TRANSCRIPTION] using transcript override", result.model_dump())
            return result

        if audio_path and Path(audio_path).exists():
            transcription = self._transcribe_with_openai(Path(audio_path))
            if transcription is not None:
                print("[TRANSCRIPTION] openai success", transcription.model_dump())
                return transcription

            fallback = TranscriptResult(
                transcript="I captured a voice note to talk through what was weighing on me.",
                source="mock_audio_file_fallback",
            )
            print("[TRANSCRIPTION] fallback after audio upload", fallback.model_dump())
            return fallback

        fallback = TranscriptResult(
            transcript="I had a stressful moment today and needed a place to talk it through.",
            source="mock_default",
        )
        print("[TRANSCRIPTION] default fallback", fallback.model_dump())
        return fallback

    def _transcribe_with_openai(self, audio_path: Path) -> TranscriptResult | None:
        if self.client is None:
            print("[TRANSCRIPTION] skipping openai transcription because client is unavailable")
            return None

        try:
            print(
                "[TRANSCRIPTION] sending file to OpenAI",
                {"audio_path": str(audio_path), "model": settings.openai_transcription_model},
            )
            with audio_path.open("rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=settings.openai_transcription_model,
                    file=audio_file,
                )
            transcript = response if isinstance(response, str) else getattr(response, "text", None)
            if transcript and transcript.strip():
                return TranscriptResult(
                    transcript=transcript.strip(),
                    source=f"openai_transcription:{settings.openai_transcription_model}",
                )
        except Exception as exc:  # pragma: no cover - network/runtime dependency
            print("[TRANSCRIPTION] openai transcription failed", {"audio_path": str(audio_path), "error": str(exc)})
            logger.warning("OpenAI transcription failed for %s: %s", audio_path, exc)
        return None
