from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.signal import medfilt

from app.core.config import settings
from app.schemas.domain import (
    HeartAnalysisResult,
    HrSample,
    MultimodalSummary,
    TemporalShift,
    TextUnderstandingResult,
    ToneAnalysisResult,
    TranscriptResult,
    WindowFlags,
    WindowRecord,
)
from app.services.model_manager import ReflectModelManager
from app.utils.time import format_time_window

try:
    import librosa
    import noisereduce
    import soundfile as sf
    import torch
except ImportError:  # pragma: no cover - optional runtime dependency
    librosa = None  # type: ignore[assignment]
    noisereduce = None  # type: ignore[assignment]
    sf = None  # type: ignore[assignment]
    torch = None  # type: ignore[assignment]


RELEVANT_EMOTIONS = {
    "anxiety",
    "nervousness",
    "fear",
    "sadness",
    "disappointment",
    "remorse",
    "grief",
    "anger",
    "annoyance",
    "disapproval",
    "confusion",
    "realization",
    "relief",
    "optimism",
    "gratitude",
    "neutral",
    "caring",
    "approval",
}

GOEMOTION_VALENCE = {
    "anxiety": -0.7,
    "nervousness": -0.6,
    "fear": -0.8,
    "sadness": -0.7,
    "disappointment": -0.6,
    "remorse": -0.6,
    "grief": -0.8,
    "anger": -0.7,
    "annoyance": -0.5,
    "disapproval": -0.4,
    "confusion": -0.3,
    "neutral": 0.0,
    "realization": 0.1,
    "caring": 0.4,
    "approval": 0.5,
    "relief": 0.6,
    "optimism": 0.5,
    "gratitude": 0.7,
}

TRIGGER_LABELS = [
    "academic or work pressure",
    "feeling behind or overwhelmed",
    "uncertainty about a decision",
    "self-doubt or self-criticism",
    "interpersonal tension or conflict",
    "time scarcity",
    "physical or mental exhaustion",
    "clarity or resolution",
    "relief or recovery",
    "positive progress or accomplishment",
]

SER_VALENCE = {
    "angry": -0.7,
    "sad": -0.5,
    "neutral": 0.0,
    "happy": 0.6,
    "calm": 0.0,
}

SELF_TALK_MARKERS = [
    "i should have",
    "i keep replaying",
    "i am behind",
    "why didn't i",
    "i made it through",
    "i'm failing",
    "i'm not enough",
]


@dataclass
class AudioArtifacts:
    waveform: np.ndarray | None
    sample_rate: int
    duration_sec: float
    trimmed_duration_sec: float
    clipping_ratio: float
    mean_rms: float
    denoise_applied: bool
    trim_offsets: tuple[float, float]
    warnings: list[str]


@dataclass
class ReflectV2Execution:
    tone_result: ToneAnalysisResult
    heart_result: HeartAnalysisResult
    text_result: TextUnderstandingResult
    multimodal_summary: MultimodalSummary
    window_records: list[WindowRecord]
    session_theme_scores: dict[str, float]
    ingestion: dict[str, Any]
    preprocessing: dict[str, Any]
    fallback_reasons: list[str]


class ReflectV2Service:
    def __init__(self) -> None:
        self.models = ReflectModelManager()

    def analyze(
        self,
        *,
        session_timestamp,
        transcript_result: TranscriptResult,
        audio_path: str | None,
        transcript_override: str | None,
        hr_log: list[dict[str, Any]] | None,
        avg_hr: float | None,
        peak_hr: float | None,
        baseline_delta: float | None,
        tone_labels_override: list[str] | None,
        tone_preset: str | None,
    ) -> ReflectV2Execution:
        fallback_reasons: list[str] = []
        ingestion = {
            "audio_path": audio_path,
            "warnings": [],
            "rejections": [],
        }

        audio = self._prepare_audio(audio_path, transcript_override)
        ingestion["warnings"].extend(audio.warnings)

        hr_artifacts = self._prepare_hr_log(
            session_timestamp_ms=int(session_timestamp.timestamp() * 1000),
            hr_log=hr_log,
            avg_hr=avg_hr,
            peak_hr=peak_hr,
            baseline_delta=baseline_delta,
        )
        ingestion["warnings"].extend(hr_artifacts["warnings"])
        ingestion["normalized_hr_log"] = [sample.model_dump() for sample in hr_artifacts["samples"]]

        window_contexts = self._build_window_contexts(
            transcript_result=transcript_result,
            audio=audio,
            session_timestamp_ms=int(session_timestamp.timestamp() * 1000),
            hr_samples=hr_artifacts["samples"],
        )
        print(
            "[REFLECT_V2] window build",
            {
                "window_count": len(window_contexts),
                "alignment_mode": (
                    "timestamp_aligned"
                    if transcript_result.words
                    else ("segment_aligned" if transcript_result.segments else "session_level_approximate")
                ),
                "audio_duration_sec": audio.trimmed_duration_sec,
                "hr_sample_count": len(hr_artifacts["samples"]),
            },
        )
        if not window_contexts:
            window_contexts = self._fallback_windows(transcript_result.transcript)
            fallback_reasons.append("window_fallback")
            print("[REFLECT_V2] window fallback applied", {"reason": "no_window_contexts"})

        print(
            "[REFLECT_V2] ingestion/preprocessing",
            {
                "ingestion_warnings": ingestion["warnings"],
                "audio": {
                    "duration_sec": audio.duration_sec,
                    "trimmed_duration_sec": audio.trimmed_duration_sec,
                    "clipping_ratio": audio.clipping_ratio,
                    "mean_rms": audio.mean_rms,
                    "denoise_applied": audio.denoise_applied,
                    "trim_offsets": audio.trim_offsets,
                },
                "hr": {
                    "used_proxy": hr_artifacts["used_proxy"],
                    "sample_count": len(hr_artifacts["samples"]),
                    "warnings": hr_artifacts["warnings"],
                },
            },
        )

        self._apply_go_emotions(window_contexts)
        session_theme_scores = self._score_session_themes(transcript_result.transcript)
        self._apply_trigger_scores(window_contexts, session_theme_scores)
        self._apply_acoustic_features(window_contexts)
        self._apply_ser(window_contexts)
        self._apply_hr_features(window_contexts)

        print(
            "[REFLECT_V2] window records",
            [
                {
                    "index": index,
                    "t_start": context["record"].t_start,
                    "t_end": context["record"].t_end,
                    "word_count": context["record"].word_count,
                    "has_text": bool(context["record"].text),
                    "text_alignment_mode": context.get("text_alignment_mode"),
                    "audio_samples": len(context["audio_slice"]) if context["audio_slice"] is not None else 0,
                    "hr_samples": len(context["hr_samples"]),
                    "flags": context["record"].flags.model_dump(),
                }
                for index, context in enumerate(window_contexts)
            ],
        )

        window_records = [context["record"] for context in window_contexts]
        multimodal_summary = self._summarize_session(
            session_timestamp=session_timestamp,
            transcript=transcript_result.transcript,
            transcript_result=transcript_result,
            window_records=window_records,
            session_theme_scores=session_theme_scores,
        )
        print("[REFLECT_V2] multimodal summary", multimodal_summary.model_dump())

        tone_result = self._build_tone_result(window_records, multimodal_summary, tone_labels_override, tone_preset)
        heart_result = self._build_heart_result(window_records, multimodal_summary, hr_artifacts["used_proxy"])
        text_result = self._build_text_result(transcript_result.transcript, window_records, session_theme_scores, multimodal_summary)

        return ReflectV2Execution(
            tone_result=tone_result,
            heart_result=heart_result,
            text_result=text_result,
            multimodal_summary=multimodal_summary,
            window_records=window_records,
            session_theme_scores=session_theme_scores,
            ingestion=ingestion,
            preprocessing={
                "audio": {
                    "duration_sec": audio.duration_sec,
                    "trimmed_duration_sec": audio.trimmed_duration_sec,
                    "clipping_ratio": audio.clipping_ratio,
                    "mean_rms": audio.mean_rms,
                    "denoise_applied": audio.denoise_applied,
                    "trim_offsets": list(audio.trim_offsets),
                },
                "hr": {
                    "used_proxy": hr_artifacts["used_proxy"],
                    "warning_count": len(hr_artifacts["warnings"]),
                    "sample_count": len(hr_artifacts["samples"]),
                },
                "text": {
                    "alignment_mode": (
                        "timestamp_aligned"
                        if transcript_result.words
                        else ("segment_aligned" if transcript_result.segments else "session_level_approximate")
                    ),
                    "has_word_timestamps": bool(transcript_result.words),
                    "has_segment_timestamps": bool(transcript_result.segments),
                },
            },
            fallback_reasons=fallback_reasons,
        )

    def _prepare_audio(self, audio_path: str | None, transcript_override: str | None) -> AudioArtifacts:
        if not audio_path:
            return AudioArtifacts(
                waveform=None,
                sample_rate=16000,
                duration_sec=0.0,
                trimmed_duration_sec=0.0,
                clipping_ratio=0.0,
                mean_rms=0.0,
                denoise_applied=False,
                trim_offsets=(0.0, 0.0),
                warnings=["No audio uploaded; v2 audio analysis is limited."],
            )
        if sf is None or librosa is None:
            return AudioArtifacts(
                waveform=None,
                sample_rate=16000,
                duration_sec=0.0,
                trimmed_duration_sec=0.0,
                clipping_ratio=0.0,
                mean_rms=0.0,
                denoise_applied=False,
                trim_offsets=(0.0, 0.0),
                warnings=["Audio libraries unavailable; skipping waveform analysis."],
            )

        warnings: list[str] = []
        try:
            waveform, sample_rate = self._load_audio_file(audio_path)
        except Exception as exc:
            warnings.append(f"Audio decoding fallback failed: {exc}")
            return AudioArtifacts(
                waveform=None,
                sample_rate=16000,
                duration_sec=0.0,
                trimmed_duration_sec=0.0,
                clipping_ratio=0.0,
                mean_rms=0.0,
                denoise_applied=False,
                trim_offsets=(0.0, 0.0),
                warnings=warnings,
            )

        if sample_rate != 16000:
            warnings.append(f"Expected 16kHz mono audio; resampled from {sample_rate}Hz.")
            waveform = librosa.resample(waveform, orig_sr=sample_rate, target_sr=16000)
            sample_rate = 16000

        duration_sec = float(len(waveform) / sample_rate) if len(waveform) else 0.0
        if duration_sec and duration_sec < 5:
            raise ValueError("Recording is too short for analysis. Please capture at least 5 seconds.")
        if duration_sec > 300:
            raise ValueError("Recording is too long for analysis. Please keep clips under 5 minutes.")

        clipping_ratio = float(np.mean(np.abs(waveform) >= 0.999)) if len(waveform) else 0.0
        if clipping_ratio > 0.05:
            warnings.append("Audio clipping exceeded 5% of samples.")

        frame_rms = librosa.feature.rms(y=waveform)[0] if len(waveform) else np.array([0.0])
        mean_rms = float(np.mean(frame_rms))
        if mean_rms < 0.003 and not transcript_override:
            raise ValueError("Recording did not contain enough usable speech energy for analysis.")

        denoise_applied = False
        noise_floor_rms = float(np.percentile(frame_rms, 15)) if len(frame_rms) else 0.0
        if noisereduce is not None and noise_floor_rms > 0.01 and len(waveform):
            waveform = noisereduce.reduce_noise(y=waveform, sr=sample_rate, stationary=True)
            denoise_applied = True

        trimmed, indices = librosa.effects.trim(waveform, top_db=25)
        if len(trimmed):
            waveform = trimmed
        trim_offsets = (float(indices[0] / sample_rate), float(indices[1] / sample_rate)) if len(indices) == 2 else (0.0, duration_sec)
        trimmed_duration_sec = float(len(waveform) / sample_rate) if len(waveform) else 0.0

        return AudioArtifacts(
            waveform=waveform,
            sample_rate=sample_rate,
            duration_sec=duration_sec,
            trimmed_duration_sec=trimmed_duration_sec,
            clipping_ratio=clipping_ratio,
            mean_rms=mean_rms,
            denoise_applied=denoise_applied,
            trim_offsets=trim_offsets,
            warnings=warnings,
        )

    def _load_audio_file(self, audio_path: str) -> tuple[np.ndarray, int]:
        waveform = None
        sample_rate = None
        soundfile_error = None

        try:
            waveform, sample_rate = sf.read(audio_path, always_2d=False)
            waveform = np.asarray(waveform, dtype=np.float32)
            if waveform.ndim > 1:
                waveform = waveform.mean(axis=1)
            return waveform, int(sample_rate)
        except Exception as exc:
            soundfile_error = exc

        # librosa can fall back to audioread/ffmpeg for formats like .m4a.
        waveform, sample_rate = librosa.load(audio_path, sr=None, mono=True)
        waveform = np.asarray(waveform, dtype=np.float32)
        if len(waveform) == 0 and soundfile_error is not None:
            raise RuntimeError(f"{soundfile_error}")
        return waveform, int(sample_rate)

    def _prepare_hr_log(
        self,
        *,
        session_timestamp_ms: int,
        hr_log: list[dict[str, Any]] | None,
        avg_hr: float | None,
        peak_hr: float | None,
        baseline_delta: float | None,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        samples: list[HrSample] = []
        used_proxy = False
        if hr_log:
            for item in hr_log:
                bpm = float(item.get("bpm", 0))
                if 40 <= bpm <= 180:
                    ir = int(item["ir"]) if item.get("ir") is not None else None
                    samples.append(HrSample(t=int(item["t"]), bpm=bpm, ir=ir))
            samples.sort(key=lambda sample: sample.t)
        elif avg_hr is not None or peak_hr is not None:
            used_proxy = True
            base = float(avg_hr or peak_hr or 72)
            peak = float(peak_hr or base)
            spread = float(baseline_delta or max(0, peak - base))
            synthetic = [
                (0, max(40.0, base - min(3.0, spread / 4))),
                (5000, base),
                (10000, peak),
                (15000, base + spread / 3 if spread else base),
            ]
            samples = [
                HrSample(t=session_timestamp_ms + offset, bpm=float(value), interpolated=True, quality=0.45)
                for offset, value in synthetic
            ]
            warnings.append("Heart-rate stream missing; using approximate summary-derived proxy samples.")

        if not samples:
            warnings.append("No heart-rate samples available.")
            return {"samples": [], "warnings": warnings, "used_proxy": used_proxy}

        bpm_series = np.array([sample.bpm for sample in samples], dtype=np.float32)
        kernel_size = 5 if len(bpm_series) >= 5 else (3 if len(bpm_series) >= 3 else 1)
        smoothed = medfilt(bpm_series, kernel_size=kernel_size) if kernel_size > 1 else bpm_series
        normalized: list[HrSample] = []
        for index, sample in enumerate(samples):
            quality = 1.0
            if sample.ir is not None and sample.ir < 50000:
                quality *= 0.35
                warnings.append("Low-contact heart-rate samples detected.")
            normalized.append(
                HrSample(
                    t=sample.t,
                    bpm=float(smoothed[index]),
                    ir=sample.ir,
                    interpolated=sample.interpolated,
                    quality=round(float(quality), 3),
                )
            )

        gap_filled: list[HrSample] = []
        for current, nxt in zip(normalized, normalized[1:]):
            gap_filled.append(current)
            gap_sec = (nxt.t - current.t) / 1000
            if 1 < gap_sec < 10:
                steps = int(gap_sec) - 1
                for offset in range(1, steps + 1):
                    ratio = offset / int(gap_sec)
                    gap_filled.append(
                        HrSample(
                            t=current.t + offset * 1000,
                            bpm=float(current.bpm + (nxt.bpm - current.bpm) * ratio),
                            ir=current.ir,
                            interpolated=True,
                            quality=round(float(((current.quality or 0.6) + (nxt.quality or 0.6)) / 2), 3),
                        )
                    )
            elif gap_sec >= 10:
                warnings.append("Long heart-rate gaps were left missing instead of interpolated.")
        gap_filled.append(normalized[-1])
        return {"samples": gap_filled, "warnings": warnings, "used_proxy": used_proxy}

    def _build_window_contexts(
        self,
        *,
        transcript_result: TranscriptResult,
        audio: AudioArtifacts,
        session_timestamp_ms: int,
        hr_samples: list[HrSample],
    ) -> list[dict[str, Any]]:
        words = transcript_result.words
        segments = transcript_result.segments
        hr_duration = 0.0
        if hr_samples:
            hr_duration = max(0.0, (hr_samples[-1].t - session_timestamp_ms) / 1000)
        session_duration = max(
            audio.trimmed_duration_sec,
            words[-1].end if words else 0.0,
            segments[-1].end if segments else 0.0,
            hr_duration,
            15.0 if transcript_result.transcript.strip() else 0.0,
        )
        if session_duration <= 0:
            return []

        contexts = self._build_time_windows(
            session_duration=session_duration,
            transcript=transcript_result.transcript,
            waveform=audio.waveform,
            sample_rate=audio.sample_rate,
            session_timestamp_ms=session_timestamp_ms,
            hr_samples=hr_samples,
        )

        if not words and segments:
            for context in contexts:
                record = context["record"]
                start = record.t_start
                end = record.t_end
                window_segments = [segment for segment in segments if segment.start < end and segment.end >= start]
                text = " ".join(segment.text for segment in window_segments if segment.text.strip()).strip()
                if not text and start <= segments[0].start and transcript_result.transcript.strip():
                    text = transcript_result.transcript.strip()
                segment_word_count = len(text.split())
                no_speech_scores = [segment.no_speech_prob for segment in window_segments if segment.no_speech_prob is not None]
                record.text = text
                record.word_count = segment_word_count
                record.text_confidence = None
                record.no_speech_prob = float(np.mean(no_speech_scores)) if no_speech_scores else None
                record.flags.low_information = segment_word_count < 10
                record.flags.low_transcript = True
                context["text_alignment_mode"] = "segment_aligned"
            return contexts

        if not words:
            transcript_text = transcript_result.transcript.strip()
            transcript_word_count = len(transcript_text.split())
            for index, context in enumerate(contexts):
                record = context["record"]
                if index == 0 and transcript_text:
                    record.text = transcript_text
                    record.word_count = transcript_word_count
                    record.flags.low_information = transcript_word_count < 10
                else:
                    record.text = ""
                    record.word_count = 0
                    record.flags.low_information = True
                record.text_confidence = None
                record.no_speech_prob = None
                record.flags.low_transcript = True
                context["text_alignment_mode"] = "session_level_approximate"
            return contexts

        for context in contexts:
            record = context["record"]
            start = record.t_start
            end = record.t_end
            window_words = [word for word in words if word.start < end and word.end >= start]
            window_segments = [
                segment for segment in transcript_result.segments if segment.start < end and segment.end >= start
            ]
            record.text = " ".join(word.word for word in window_words).strip()
            record.word_count = len(window_words)
            word_probs = [word.probability for word in window_words if word.probability is not None]
            record.text_confidence = float(np.mean(word_probs)) if word_probs else None
            no_speech_scores = [segment.no_speech_prob for segment in window_segments if segment.no_speech_prob is not None]
            record.no_speech_prob = float(np.mean(no_speech_scores)) if no_speech_scores else None
            record.flags.low_information = len(window_words) < 10
            record.flags.low_transcript = (record.text_confidence or 1.0) < 0.65
            context["text_alignment_mode"] = "timestamp_aligned"
        return contexts

    def _build_time_windows(
        self,
        *,
        session_duration: float,
        transcript: str,
        waveform: np.ndarray | None,
        sample_rate: int,
        session_timestamp_ms: int,
        hr_samples: list[HrSample],
    ) -> list[dict[str, Any]]:
        contexts: list[dict[str, Any]] = []
        window_length = 15.0
        stride = 7.0
        start = 0.0
        transcript_text = transcript.strip()
        transcript_word_count = len(transcript_text.split())
        while start < session_duration:
            end = min(start + window_length, session_duration)
            audio_slice = None
            if waveform is not None and sample_rate:
                start_index = max(0, int(start * sample_rate))
                end_index = max(start_index + 1, int(end * sample_rate))
                audio_slice = waveform[start_index:end_index]
            hr_window = [
                sample for sample in hr_samples if start <= (sample.t - session_timestamp_ms) / 1000 <= end
            ]
            record = WindowRecord(
                t_start=round(start, 2),
                t_end=round(end, 2),
                text=transcript_text if len(contexts) == 0 else "",
                word_count=transcript_word_count if len(contexts) == 0 else 0,
                text_confidence=None,
                no_speech_prob=None,
                flags=WindowFlags(
                    low_information=(transcript_word_count if len(contexts) == 0 else 0) < 10,
                    low_transcript=True,
                ),
            )
            contexts.append({"record": record, "audio_slice": audio_slice, "hr_samples": hr_window})
            if end >= session_duration:
                break
            start += stride
        return contexts

    def _fallback_windows(self, transcript: str, session_duration: float = 15.0) -> list[dict[str, Any]]:
        text = transcript.strip() or "A short reflection was captured without aligned timestamps."
        record = WindowRecord(
            t_start=0.0,
            t_end=round(session_duration, 2),
            text=text,
            word_count=len(text.split()),
            text_confidence=None,
            no_speech_prob=None,
            flags=WindowFlags(low_information=len(text.split()) < 10, low_transcript=True),
        )
        return [{"record": record, "audio_slice": None, "hr_samples": []}]

    def _apply_go_emotions(self, window_contexts: list[dict[str, Any]]) -> None:
        classifier = self.models.get_go_emotions()
        texts = [context["record"].text for context in window_contexts if context["record"].text and not context["record"].flags.low_information]
        if classifier is None or not texts:
            print(
                "[REFLECT_V2] go_emotions skipped",
                {"classifier_available": classifier is not None, "eligible_text_windows": len(texts)},
            )
            return

        raw_outputs = classifier(texts)
        if raw_outputs and isinstance(raw_outputs[0], dict):
            raw_outputs = [raw_outputs]

        output_index = 0
        for context in window_contexts:
            record = context["record"]
            if record.flags.low_information:
                continue
            labels = raw_outputs[output_index]
            output_index += 1
            filtered = {
                item["label"]: float(item["score"])
                for item in labels
                if item["label"] in RELEVANT_EMOTIONS
            }
            active = {label: score for label, score in filtered.items() if score > settings.reflect_goemotions_threshold}
            if not active:
                top_two = sorted(filtered.items(), key=lambda item: item[1], reverse=True)[:2]
                active = {label: float(score) for label, score in top_two}
            record.go_emotions = dict(sorted(active.items(), key=lambda item: item[1], reverse=True))
            record.text_valence = round(
                sum(score * GOEMOTION_VALENCE.get(label, 0.0) for label, score in record.go_emotions.items()),
                4,
            )
            record.activation_magnitude = round(sum(record.go_emotions.values()), 4)
            print(
                "[REFLECT_V2] go_emotions window",
                {
                    "t_start": record.t_start,
                    "t_end": record.t_end,
                    "text_preview": record.text[:120],
                    "active_labels": record.go_emotions,
                    "text_valence": record.text_valence,
                    "activation_magnitude": record.activation_magnitude,
                },
            )

    def _score_session_themes(self, transcript: str) -> dict[str, float]:
        classifier = self.models.get_zero_shot()
        if classifier is None or not transcript.strip():
            print(
                "[REFLECT_V2] session themes skipped",
                {"classifier_available": classifier is not None, "has_transcript": bool(transcript.strip())},
            )
            return {}
        result = classifier(transcript, candidate_labels=TRIGGER_LABELS, multi_label=True)
        scores = {
            label: round(float(score), 4)
            for label, score in zip(result.get("labels", []), result.get("scores", []))
        }
        print("[REFLECT_V2] session themes", scores)
        return scores

    def _apply_trigger_scores(self, window_contexts: list[dict[str, Any]], session_theme_scores: dict[str, float]) -> None:
        classifier = self.models.get_zero_shot()
        if classifier is None:
            print("[REFLECT_V2] trigger scoring skipped", {"classifier_available": False})
            return
        flagged = [
            context
            for context in sorted(window_contexts, key=lambda item: item["record"].activation_magnitude, reverse=True)
            if context["record"].text.strip() and context.get("text_alignment_mode") == "timestamp_aligned"
        ][:3]
        texts = [context["record"].text for context in flagged]
        if not texts:
            top_session_trigger = [label for label, score in session_theme_scores.items() if score > 0.40][:3]
            if not top_session_trigger and session_theme_scores:
                top_session_trigger = [max(session_theme_scores, key=session_theme_scores.get)]
            for context in window_contexts:
                if not context["record"].trigger_labels:
                    context["record"].trigger_labels = {label: session_theme_scores.get(label, 0.0) for label in top_session_trigger}
            print(
                "[REFLECT_V2] trigger scoring session-only",
                {"top_session_triggers": top_session_trigger, "window_count": len(window_contexts)},
            )
            return
        results = classifier(texts, candidate_labels=TRIGGER_LABELS, multi_label=True)
        if isinstance(results, dict):
            results = [results]
        result_index = 0
        for context in flagged:
            if not context["record"].text.strip():
                continue
            result = results[result_index]
            result_index += 1
            active = {
                label: round(float(score), 4)
                for label, score in zip(result.get("labels", []), result.get("scores", []))
                if score > 0.40
            }
            if not active and result.get("labels"):
                active = {result["labels"][0]: round(float(result["scores"][0]), 4)}
            context["record"].trigger_labels = active
            print(
                "[REFLECT_V2] trigger window",
                {
                    "t_start": context["record"].t_start,
                    "t_end": context["record"].t_end,
                    "trigger_labels": active,
                },
            )

        top_session_trigger = [label for label, score in session_theme_scores.items() if score > 0.40][:3]
        if not top_session_trigger and session_theme_scores:
            top_session_trigger = [max(session_theme_scores, key=session_theme_scores.get)]
        for context in window_contexts:
            if not context["record"].trigger_labels:
                context["record"].trigger_labels = {label: session_theme_scores.get(label, 0.0) for label in top_session_trigger}
        print("[REFLECT_V2] trigger scoring complete", {"top_session_triggers": top_session_trigger})

    def _apply_acoustic_features(self, window_contexts: list[dict[str, Any]]) -> None:
        if librosa is None:
            print("[REFLECT_V2] acoustic features skipped", {"librosa_available": False})
            return
        pitch_stds: list[float | None] = []
        energy_means: list[float | None] = []
        pause_ratios: list[float | None] = []
        for context in window_contexts:
            audio_slice = context["audio_slice"]
            record = context["record"]
            if audio_slice is None or len(audio_slice) < 1024:
                pitch_stds.append(None)
                energy_means.append(None)
                pause_ratios.append(None)
                print(
                    "[REFLECT_V2] acoustic window skipped",
                    {
                        "t_start": record.t_start,
                        "t_end": record.t_end,
                        "audio_samples": len(audio_slice) if audio_slice is not None else 0,
                    },
                )
                continue
            try:
                f0, voiced_flag, voiced_probs = librosa.pyin(audio_slice, fmin=80, fmax=400, sr=16000)
                mask = (voiced_flag == True) & (np.nan_to_num(voiced_probs, nan=0.0) > 0.5)  # noqa: E712
                voiced = f0[mask] if f0 is not None else np.array([])
                pitch_mean = float(np.nanmean(voiced)) if len(voiced) else None
                pitch_std = float(np.nanstd(voiced)) if len(voiced) else None
                rms = librosa.feature.rms(y=audio_slice)[0]
                energy_mean = float(np.mean(rms))
                intervals = librosa.effects.split(audio_slice, top_db=30)
                voiced_dur = float(sum(end - start for start, end in intervals) / 16000) if len(intervals) else 0.0
                pause_ratio = float(max(0.0, 1.0 - (voiced_dur / max(len(audio_slice) / 16000, 1e-6))))
                record.pitch_mean = pitch_mean
                record.pitch_std = pitch_std
                record.energy_mean = energy_mean
                record.pause_ratio = pause_ratio
                pitch_stds.append(pitch_std)
                energy_means.append(energy_mean)
                pause_ratios.append(pause_ratio)
                print(
                    "[REFLECT_V2] acoustic window",
                    {
                        "t_start": record.t_start,
                        "t_end": record.t_end,
                        "pitch_mean": record.pitch_mean,
                        "pitch_std": record.pitch_std,
                        "energy_mean": record.energy_mean,
                        "pause_ratio": record.pause_ratio,
                    },
                )
            except Exception:
                pitch_stds.append(None)
                energy_means.append(None)
                pause_ratios.append(None)
                print(
                    "[REFLECT_V2] acoustic window failed",
                    {"t_start": record.t_start, "t_end": record.t_end},
                )

        pitch_z = self._zscore(pitch_stds)
        energy_z = self._zscore(energy_means)
        pause_z = self._zscore(pause_ratios)
        for index, context in enumerate(window_contexts):
            context["record"].acoustic_observations = {
                "energy": self._bucketize(energy_z[index]),
                "pitch_variability": self._bucketize(pitch_z[index]),
                "pause_density": self._pause_bucket(context["record"].pause_ratio),
            }
            print(
                "[REFLECT_V2] acoustic observations window",
                {
                    "t_start": context["record"].t_start,
                    "t_end": context["record"].t_end,
                    "observations": context["record"].acoustic_observations,
                },
            )

    def _apply_ser(self, window_contexts: list[dict[str, Any]]) -> None:
        classifier = self.models.get_ser()
        if classifier is None or torch is None:
            print(
                "[REFLECT_V2] ser skipped",
                {"classifier_available": classifier is not None, "torch_available": torch is not None},
            )
            return
        eligible = [
            (index, context)
            for index, context in enumerate(window_contexts)
            if context["audio_slice"] is not None
            and len(context["audio_slice"]) > 1600
            and (context["record"].no_speech_prob or 0.0) <= 0.6
        ]
        if not eligible:
            print("[REFLECT_V2] ser skipped", {"reason": "no_eligible_windows"})
            return

        with ThreadPoolExecutor(max_workers=max(1, settings.reflect_ser_workers)) as executor:
            results = list(executor.map(lambda item: self._run_ser_window(classifier, item[1]["audio_slice"]), eligible))

        for (index, _), result in zip(eligible, results):
            if not result or result.get("error"):
                print(
                    "[REFLECT_V2] ser window failed",
                    {
                        "t_start": window_contexts[index]["record"].t_start,
                        "t_end": window_contexts[index]["record"].t_end,
                        "error": None if not result else result.get("error"),
                    },
                )
                continue
            record = window_contexts[index]["record"]
            record.ser_scores = result["scores"]
            record.ser_valence = result["ser_valence"]
            record.ser_arousal = result["ser_arousal"]
            record.delivery_divergence = (
                abs((record.text_valence or 0.0) - result["ser_valence"])
                if record.text_valence is not None
                else None
            )
            record.flags.ser_available = True
            record.flags.tone_mismatch = bool(record.delivery_divergence is not None and record.delivery_divergence > 0.5)
            print(
                "[REFLECT_V2] ser window",
                {
                    "t_start": record.t_start,
                    "t_end": record.t_end,
                    "ser_scores": record.ser_scores,
                    "ser_valence": record.ser_valence,
                    "ser_arousal": record.ser_arousal,
                    "delivery_divergence": record.delivery_divergence,
                    "tone_mismatch": record.flags.tone_mismatch,
                },
            )

    def _run_ser_window(self, classifier, audio_slice: np.ndarray) -> dict[str, Any] | None:
        try:
            waveform = torch.tensor(audio_slice, dtype=torch.float32).unsqueeze(0)
            out_prob, _, _, _ = classifier.classify_batch(waveform)
            probabilities = out_prob[0].detach().cpu().numpy()
            label_list = getattr(classifier, "labels", None)
            if label_list:
                scores = {
                    str(label_list[index] if index < len(label_list) else index): round(float(prob), 4)
                    for index, prob in enumerate(probabilities)
                }
            else:
                hparams = getattr(classifier, "hparams", None)
                label_map = getattr(getattr(hparams, "label_encoder", None), "ind2lab", None) or {}
                scores = {
                    str(label_map.get(index, index)): round(float(prob), 4)
                    for index, prob in enumerate(probabilities)
                }
            normalized = {self._normalize_ser_label(label): score for label, score in scores.items()}
            ser_valence = round(sum(score * SER_VALENCE.get(label, 0.0) for label, score in normalized.items()), 4)
            ser_arousal = round(normalized.get("angry", 0.0) + normalized.get("happy", 0.0), 4)
            return {"scores": normalized, "ser_valence": ser_valence, "ser_arousal": ser_arousal}
        except Exception as exc:
            return {"error": str(exc)}

    def _apply_hr_features(self, window_contexts: list[dict[str, Any]]) -> None:
        means: list[float | None] = []
        for context in window_contexts:
            record = context["record"]
            samples: list[HrSample] = context["hr_samples"]
            if not samples:
                means.append(None)
                print(
                    "[REFLECT_V2] hr window skipped",
                    {"t_start": record.t_start, "t_end": record.t_end, "reason": "no_samples"},
                )
                continue
            bpms = np.array([sample.bpm for sample in samples], dtype=np.float32)
            qualities = [sample.quality for sample in samples if sample.quality is not None]
            mean_quality = float(np.mean(qualities)) if qualities else 0.0
            record.hr_quality = round(mean_quality, 4)
            if mean_quality < 0.5:
                means.append(None)
                print(
                    "[REFLECT_V2] hr window suppressed",
                    {
                        "t_start": record.t_start,
                        "t_end": record.t_end,
                        "hr_quality": record.hr_quality,
                    },
                )
                continue
            timestamps = np.array([(sample.t - samples[0].t) / 1000 for sample in samples], dtype=np.float32)
            slope = float(np.polyfit(timestamps, bpms, 1)[0]) if len(samples) > 1 and len(set(timestamps.tolist())) > 1 else 0.0
            record.hr_mean_bpm = float(np.mean(bpms))
            record.hr_peak_bpm = float(np.max(bpms))
            record.hr_bpm_range = float(np.max(bpms) - np.min(bpms))
            record.hr_slope = slope
            record.flags.hr_available = True
            means.append(record.hr_mean_bpm)
            print(
                "[REFLECT_V2] hr window",
                {
                    "t_start": record.t_start,
                    "t_end": record.t_end,
                    "hr_mean_bpm": record.hr_mean_bpm,
                    "hr_peak_bpm": record.hr_peak_bpm,
                    "hr_bpm_range": record.hr_bpm_range,
                    "hr_slope": record.hr_slope,
                    "hr_quality": record.hr_quality,
                },
            )

        valid_means = [value for value in means if value is not None]
        session_mean = float(np.mean(valid_means)) if valid_means else 0.0
        session_std = float(np.std(valid_means)) if len(valid_means) > 1 else 0.0
        threshold = session_mean + (1.5 * session_std)
        for context in window_contexts:
            record = context["record"]
            if record.hr_mean_bpm is not None:
                record.hr_elevated = bool(record.hr_mean_bpm > threshold if session_std else record.hr_mean_bpm > session_mean + 3)
                print(
                    "[REFLECT_V2] hr elevation window",
                    {
                        "t_start": record.t_start,
                        "t_end": record.t_end,
                        "hr_mean_bpm": record.hr_mean_bpm,
                        "threshold": threshold,
                        "hr_elevated": record.hr_elevated,
                    },
                )

    def _summarize_session(
        self,
        *,
        session_timestamp,
        transcript: str,
        transcript_result: TranscriptResult,
        window_records: list[WindowRecord],
        session_theme_scores: dict[str, float],
    ) -> MultimodalSummary:
        classifiable = [record for record in window_records if not record.flags.low_information and record.go_emotions]
        emotion_counts = Counter(
            label for record in classifiable for label in record.go_emotions
        )
        dominant_emotions = [
            label
            for label, count in emotion_counts.items()
            if count >= max(1, int(np.ceil(len(classifiable) * 0.4)))
        ]
        if not dominant_emotions and emotion_counts:
            dominant_emotions = [emotion_counts.most_common(1)[0][0]]

        valence_series = [record.text_valence or 0.0 for record in classifiable]
        smoothed = self._rolling_mean(valence_series, window=3)
        deltas = np.diff(smoothed) if len(smoothed) > 1 else np.array([])
        shift_threshold = float(np.mean(np.abs(deltas)) + 1.5 * np.std(deltas)) if len(deltas) else 0.0
        largest_negative_shift = None
        largest_positive_shift = None
        for index, delta in enumerate(deltas):
            if delta < -shift_threshold and (largest_negative_shift is None or delta < largest_negative_shift[1]):
                largest_negative_shift = (index + 1, float(delta))
            if delta > shift_threshold and (largest_positive_shift is None or delta > largest_positive_shift[1]):
                largest_positive_shift = (index + 1, float(delta))

        primary_shift = largest_negative_shift or largest_positive_shift or (0, 0.0)
        shift_index = min(primary_shift[0], max(len(classifiable) - 1, 0))
        shift_record = classifiable[shift_index] if classifiable else (window_records[0] if window_records else None)
        previous_record = classifiable[max(0, shift_index - 1)] if classifiable else shift_record
        shift = TemporalShift(
            direction="negative" if largest_negative_shift else ("positive" if largest_positive_shift else "flat"),
            at_seconds=round(shift_record.t_start if shift_record else 0.0, 2),
            preceding_text=(previous_record.text[:180] if previous_record else ""),
            shift_window_text=(shift_record.text[:180] if shift_record else ""),
            hr_elevated_at_shift=bool(shift_record.hr_elevated) if shift_record else False,
            tone_mismatch_at_shift=bool(shift_record.flags.tone_mismatch) if shift_record else False,
        )

        session_mean_valence = float(np.mean(valence_series)) if valence_series else 0.0
        recovery_detected = False
        if largest_negative_shift and len(smoothed) > largest_negative_shift[0]:
            post_shift = smoothed[largest_negative_shift[0]:]
            recovery_detected = any(value >= session_mean_valence - abs(primary_shift[1]) * 0.5 for value in post_shift)

        repeated_triggers = [
            label
            for label, score in session_theme_scores.items()
            if score > 0.40 and any(label in record.trigger_labels for record in classifiable)
        ]
        if not repeated_triggers and session_theme_scores:
            repeated_triggers = [max(session_theme_scores, key=session_theme_scores.get)]

        mismatch_ratio = (
            sum(1 for record in classifiable if record.flags.tone_mismatch) / len(classifiable)
            if classifiable
            else 0.0
        )
        tone_mismatch_present = mismatch_ratio > 0.30

        strongest = max(classifiable, key=lambda record: record.activation_magnitude, default=shift_record)
        hardest_windows = [
            f"{format_time_window(session_timestamp)} ({round(record.t_start)}s)"
            for record in sorted(classifiable, key=lambda item: item.activation_magnitude, reverse=True)[:3]
        ]
        quotes = [item for item in [strongest.text if strongest else "", previous_record.text if previous_record else ""] if item]
        confidence_notes: list[str] = []
        word_probs = [word.probability for word in transcript_result.words if word.probability is not None]
        if word_probs and float(np.mean(word_probs)) < 0.65:
            confidence_notes.append("language-based observations may be less reliable due to audio quality")
        hr_available_windows = [record for record in window_records if record.flags.hr_available]
        if window_records and len(hr_available_windows) < max(1, len(window_records) / 2):
            confidence_notes.append("heart rate data was unreliable and is not included")
        if len(classifiable) < 5:
            confidence_notes.append("session was brief; patterns are based on limited data")
        if window_records and (sum(1 for record in window_records if record.flags.low_information) / len(window_records)) > 0.30:
            confidence_notes.append("significant portions of the session had insufficient speech for analysis")
        if not transcript_result.words:
            if transcript_result.segments:
                confidence_notes.append("text timing used coarse transcript segments rather than word-level timestamps")
            else:
                confidence_notes.append("text analysis stayed session-level because transcript timestamps were unavailable")
                confidence_notes.append("temporal transcript alignment was limited; audio and heart-rate windows are stronger than text timing")

        arc_text = self._describe_arc(classifiable, smoothed)
        acoustic_observations = self._summarize_acoustics(window_records)
        mixed_feelings = self._collect_mixed_feelings(classifiable)

        return MultimodalSummary(
            session_duration_sec=round(max((window_records[-1].t_end if window_records else 0.0), 0.0), 2),
            dominant_emotions=dominant_emotions,
            emotional_arc=arc_text,
            repeated_triggers=repeated_triggers,
            largest_shift=shift,
            recovery_detected=recovery_detected,
            acoustic_observations=acoustic_observations,
            tone_mismatch_present=tone_mismatch_present,
            representative_quotes=quotes[:2],
            confidence_notes=confidence_notes,
            strongest_recovery_moment=(largest_positive_shift and classifiable[min(largest_positive_shift[0], len(classifiable) - 1)].text[:180]) or None,
            mixed_feelings=mixed_feelings,
            hardest_windows=hardest_windows,
        )

    def _build_tone_result(
        self,
        window_records: list[WindowRecord],
        summary: MultimodalSummary,
        tone_labels_override: list[str] | None,
        tone_preset: str | None,
    ) -> ToneAnalysisResult:
        classifiable = [record for record in window_records if record.go_emotions]
        top_emotions = summary.dominant_emotions or [label for label in (tone_labels_override or [])[:2]]
        if not top_emotions and tone_preset:
            top_emotions = [tone_preset]
        if not top_emotions:
            top_emotions = ["reflective"]
        tone_scores = Counter()
        ser_scores: Counter[str] = Counter()
        divergences: list[float] = []
        acoustic_notes = summary.acoustic_observations
        for record in classifiable:
            for label, score in record.go_emotions.items():
                tone_scores[label] += score
            for label, score in record.ser_scores.items():
                ser_scores[label] += score
            if record.delivery_divergence is not None:
                divergences.append(record.delivery_divergence)

        arousal_seed = np.mean([
            record.ser_arousal or 0.0
            for record in classifiable
            if record.ser_arousal is not None
        ]) if classifiable else 0.0
        arousal_level = "high" if arousal_seed > 0.5 else ("low" if arousal_seed < 0.2 else "medium")
        return ToneAnalysisResult(
            primary_labels=top_emotions[:3],
            label_scores=[
                {"label": label, "score": round(float(score), 4)}
                for label, score in tone_scores.most_common(5)
            ] or [{"label": label, "score": 0.0} for label in top_emotions[:2]],
            arousal_level=arousal_level,
            confidence=round(min(0.95, 0.45 + len(classifiable) * 0.05), 2),
            acoustic_features_summary=self._build_acoustic_sentence(acoustic_notes),
            delivery_divergence=round(float(np.mean(divergences)), 4) if divergences else None,
            tone_mismatch_ratio=round(
                sum(1 for record in classifiable if record.flags.tone_mismatch) / len(classifiable),
                4,
            ) if classifiable else None,
            ser_top_label=ser_scores.most_common(1)[0][0] if ser_scores else None,
            ser_label_scores=[
                {"label": label, "score": round(float(score), 4)}
                for label, score in ser_scores.most_common(5)
            ],
            acoustic_observations=acoustic_notes,
        )

    def _build_heart_result(
        self,
        window_records: list[WindowRecord],
        summary: MultimodalSummary,
        used_proxy: bool,
    ) -> HeartAnalysisResult:
        available = [record for record in window_records if record.flags.hr_available and record.hr_mean_bpm is not None]
        if not available:
            return HeartAnalysisResult(
                heart_activation_note="Heart data was too limited to meaningfully shape this reflection.",
                activation_flag=False,
                intensity=2,
                quality_note="No reliable heart-rate windows were available.",
                hr_available=False,
            )
        mean_bpm = float(np.mean([record.hr_mean_bpm for record in available if record.hr_mean_bpm is not None]))
        peak_bpm = float(np.max([record.hr_peak_bpm for record in available if record.hr_peak_bpm is not None]))
        mean_quality = float(np.mean([record.hr_quality or 0.0 for record in available]))
        activation_windows = [record for record in available if record.hr_elevated]
        if activation_windows:
            note = "Your body also seemed more activated around the strongest emotional moment."
            intensity = 7 if len(activation_windows) > 1 else 5
            activation_flag = True
        else:
            note = "Heart-rate activity stayed relatively steady through most of this session."
            intensity = 3
            activation_flag = False
        quality_note = "Approximate heart-rate proxy was used." if used_proxy else "Windowed heart-rate data informed the summary."
        if "heart rate data was unreliable and is not included" in summary.confidence_notes:
            note = "Heart data was inconsistent, so it did not strongly shape the interpretation."
            activation_flag = False
        return HeartAnalysisResult(
            heart_activation_note=note,
            activation_flag=activation_flag,
            intensity=intensity,
            quality_note=quality_note,
            hr_available=True,
            mean_bpm=round(mean_bpm, 2),
            peak_bpm=round(peak_bpm, 2),
            mean_quality=round(mean_quality, 3),
        )

    def _build_text_result(
        self,
        transcript: str,
        window_records: list[WindowRecord],
        session_theme_scores: dict[str, float],
        summary: MultimodalSummary,
    ) -> TextUnderstandingResult:
        lowered = transcript.lower()
        self_talk = [marker for marker in SELF_TALK_MARKERS if marker in lowered]
        repeated = [label for label, _ in Counter(summary.repeated_triggers + summary.dominant_emotions).most_common(4)]
        emotion_window_counts = Counter(
            label for record in window_records for label in record.go_emotions
        )
        mixed = summary.mixed_feelings or self._legacy_mixed_feelings(lowered)
        return TextUnderstandingResult(
            themes=[label for label, score in session_theme_scores.items() if score > 0.40][:3] or summary.repeated_triggers or ["general stress"],
            trigger_tags=(
                summary.repeated_triggers
                or ([max(session_theme_scores, key=session_theme_scores.get)] if session_theme_scores else ["general overload"])
            ),
            self_talk_markers=self_talk or ["trying to stay afloat"],
            repeated_concerns=repeated or ["recurring pressure"],
            candidate_mixed_feelings=mixed or ["stress mixed with a need for relief"],
            emotion_window_counts=dict(emotion_window_counts),
            session_theme_scores={label: round(float(score), 4) for label, score in session_theme_scores.items()},
            emotional_arc=[round(record.text_valence or 0.0, 4) for record in window_records if record.text_valence is not None],
        )

    def _normalize_ser_label(self, label: str) -> str:
        lowered = label.lower()
        if lowered.startswith("ang"):
            return "angry"
        if lowered.startswith("hap") or lowered.startswith("exc"):
            return "happy"
        if lowered.startswith("sad"):
            return "sad"
        if lowered.startswith("calm"):
            return "calm"
        return "neutral"

    def _zscore(self, values: list[float | None]) -> list[float | None]:
        valid = [value for value in values if value is not None]
        if not valid:
            return [None for _ in values]
        valid_mean = float(np.mean(valid))
        valid_std = float(np.std(valid))
        if valid_std == 0:
            return [0.0 if value is not None else None for value in values]
        return [round((value - valid_mean) / valid_std, 4) if value is not None else None for value in values]

    def _bucketize(self, z_score: float | None) -> str:
        if z_score is None:
            return "unknown"
        if z_score > 1.0:
            return "high"
        if z_score < -1.0:
            return "low"
        return "moderate"

    def _pause_bucket(self, pause_ratio: float | None) -> str:
        if pause_ratio is None:
            return "unknown"
        if pause_ratio > 0.45:
            return "heavy"
        if pause_ratio < 0.20:
            return "light"
        return "moderate"

    def _rolling_mean(self, values: list[float], window: int) -> list[float]:
        if not values:
            return []
        result = []
        for index in range(len(values)):
            subset = values[max(0, index - window + 1): index + 1]
            result.append(float(np.mean(subset)))
        return result

    def _describe_arc(self, records: list[WindowRecord], smoothed: list[float]) -> str:
        if not records:
            return "The session had limited usable speech, so the emotional arc is approximate."
        start_feeling = next(iter(records[0].go_emotions), "neutral")
        end_feeling = next(iter(records[-1].go_emotions), start_feeling)
        if len(records) == 1:
            return f"It stayed mostly {start_feeling} through the short reflection."
        peak_record = max(records, key=lambda record: record.activation_magnitude or 0.0)
        return (
            f"It started more {start_feeling}, intensified around {round(peak_record.t_start)} seconds, "
            f"and ended closer to {end_feeling}."
        )

    def _summarize_acoustics(self, window_records: list[WindowRecord]) -> dict[str, str]:
        if not window_records:
            return {"energy_trend": "unknown", "pitch_variability_trend": "unknown", "pause_density_trend": "unknown"}
        energy = Counter(record.acoustic_observations.get("energy", "unknown") for record in window_records)
        pitch = Counter(record.acoustic_observations.get("pitch_variability", "unknown") for record in window_records)
        pause = Counter(record.acoustic_observations.get("pause_density", "unknown") for record in window_records)
        return {
            "energy_trend": energy.most_common(1)[0][0],
            "pitch_variability_trend": pitch.most_common(1)[0][0],
            "pause_density_trend": pause.most_common(1)[0][0],
        }

    def _collect_mixed_feelings(self, classifiable: list[WindowRecord]) -> list[str]:
        mixed: list[str] = []
        for record in classifiable:
            if len(record.go_emotions) > 1:
                labels = list(record.go_emotions)[:2]
                mixed.append(f"{labels[0]} and {labels[1]}")
            elif record.flags.tone_mismatch and record.go_emotions:
                mixed.append(f"{next(iter(record.go_emotions))} with a more controlled delivery")
        deduped = []
        for item in mixed:
            if item not in deduped:
                deduped.append(item)
        return deduped[:3]

    def _build_acoustic_sentence(self, acoustic_notes: dict[str, str]) -> str:
        return (
            f"Energy trend looked {acoustic_notes.get('energy_trend', 'unknown')}, "
            f"pitch variability was {acoustic_notes.get('pitch_variability_trend', 'unknown')}, "
            f"and pauses were {acoustic_notes.get('pause_density_trend', 'unknown')}."
        )

    def _legacy_mixed_feelings(self, lowered: str) -> list[str]:
        mixed = []
        if "better" in lowered and "still" in lowered:
            mixed.append("relieved but still carrying tension")
        if "proud" in lowered and ("tired" in lowered or "drained" in lowered):
            mixed.append("proud but drained")
        return mixed
