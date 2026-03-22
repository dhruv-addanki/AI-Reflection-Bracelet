from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.schemas.domain import (
    HeartAnalysisResult,
    MultimodalSummary,
    SynthesisClipEvaluation,
    SynthesisDailyUpdate,
    SynthesisResult,
    TextUnderstandingResult,
    TimelineBlock,
    ToneAnalysisResult,
)
from app.utils.time import format_time_window

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional integration path
    OpenAI = None  # type: ignore[assignment]

PROMPT_VERSION = "wellness_synthesis_v2"

OPENAI_SYNTHESIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "clip_evaluation": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "string"},
                "primary_feelings": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
                "mixed_feelings": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                "trigger_tags": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "heart_activation_note": {"type": "string"},
                "support_suggestion": {"type": "string"},
                "distress_intensity": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": [
                "summary",
                "primary_feelings",
                "mixed_feelings",
                "trigger_tags",
                "heart_activation_note",
                "support_suggestion",
                "distress_intensity",
            ],
        },
        "daily_summary_update": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "hardest_moment": {"type": "string"},
                "calmest_moment": {"type": "string"},
                "most_repeated_feeling": {"type": "string"},
                "one_thing_to_notice": {"type": "string"},
                "timeline_blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string"},
                            "time_range": {"type": "string"},
                            "feeling": {"type": "string"},
                            "intensity": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "required": ["label", "time_range", "feeling", "intensity"],
                    },
                    "minItems": 1,
                    "maxItems": 4,
                },
                "end_of_day_reflection": {"type": "string"},
                "reflection_prompt": {"type": "string"},
                "mixed_feeling_insight": {"type": "string"},
            },
            "required": [
                "hardest_moment",
                "calmest_moment",
                "most_repeated_feeling",
                "one_thing_to_notice",
                "timeline_blocks",
                "end_of_day_reflection",
                "reflection_prompt",
                "mixed_feeling_insight",
            ],
        },
    },
    "required": ["clip_evaluation", "daily_summary_update"],
}


@dataclass(frozen=True)
class SynthesisExecutionResult:
    result: SynthesisResult
    provider: str
    model: str
    prompt_version: str
    fallback_reason: str | None = None
    raw_response_text: str | None = None


class GptSynthesisService:
    def synthesize_clip_and_daily_update(
        self,
        input_payload: dict[str, Any],
        multimodal_summary: MultimodalSummary,
        tone_result: ToneAnalysisResult,
        heart_result: HeartAnalysisResult,
        text_result: TextUnderstandingResult,
    ) -> SynthesisExecutionResult:
        print(
            "[SYNTHESIS] start",
            {
                "provider_attempted": "openai" if settings.openai_api_key and OpenAI is not None else "mock",
                "openai_model": settings.openai_model,
                "prompt_version": PROMPT_VERSION,
                "transcript_preview": input_payload["transcript"][:160],
                "dominant_emotions": multimodal_summary.dominant_emotions,
            },
        )
        if settings.openai_api_key and OpenAI is not None:
            synthesis = self._try_openai_structured_output(
                input_payload=input_payload,
                multimodal_summary=multimodal_summary,
                tone_result=tone_result,
                heart_result=heart_result,
                text_result=text_result,
            )
            if synthesis is not None:
                print(
                    "[SYNTHESIS] openai success",
                    {
                        "provider": synthesis.provider,
                        "model": synthesis.model,
                        "clip_summary": synthesis.result.clip_evaluation.summary,
                    },
                )
                return synthesis

        fallback_reason = "OPENAI_API_KEY missing, OpenAI SDK unavailable, or structured synthesis failed."
        timestamp = input_payload["timestamp"]
        transcript = input_payload["transcript"]
        feeling_counts = Counter(multimodal_summary.dominant_emotions + tone_result.primary_labels + text_result.candidate_mixed_feelings)
        most_repeated_feeling = feeling_counts.most_common(1)[0][0] if feeling_counts else "reflective"
        summary = self._build_summary(transcript, multimodal_summary, tone_result.primary_labels)
        support = self._build_support_suggestion(input_payload["support_style"], heart_result)

        fallback = SynthesisExecutionResult(
            result=SynthesisResult(
                clip_evaluation=SynthesisClipEvaluation(
                    summary=summary,
                    primary_feelings=(multimodal_summary.dominant_emotions or tone_result.primary_labels)[:3],
                    mixed_feelings=(multimodal_summary.mixed_feelings or text_result.candidate_mixed_feelings)[:3],
                    trigger_tags=(multimodal_summary.repeated_triggers or text_result.trigger_tags)[:5],
                    heart_activation_note=heart_result.heart_activation_note,
                    support_suggestion=support,
                    distress_intensity=self._distress_intensity(multimodal_summary, heart_result, tone_result),
                ),
                daily_summary_update=SynthesisDailyUpdate(
                    hardest_moment=f"It sounds like {summary.lower()}",
                    calmest_moment=(
                        multimodal_summary.strongest_recovery_moment[:160]
                        if multimodal_summary.strongest_recovery_moment
                        else "The steadier moment seems to come when the pressure eases slightly."
                    ),
                    most_repeated_feeling=most_repeated_feeling,
                    one_thing_to_notice=(
                        f"A recurring theme seems to be {multimodal_summary.repeated_triggers[0]}."
                        if multimodal_summary.repeated_triggers
                        else "A recurring theme seems to be pressure building around too many demands."
                    ),
                    timeline_blocks=[
                        TimelineBlock(
                            label=format_time_window(timestamp),
                            time_range=timestamp.strftime("%-I:%M %p"),
                            feeling=(multimodal_summary.dominant_emotions[0] if multimodal_summary.dominant_emotions else most_repeated_feeling),
                            intensity=self._distress_intensity(multimodal_summary, heart_result, tone_result),
                        )
                    ],
                    end_of_day_reflection=self._build_reflection_paragraph(multimodal_summary),
                    reflection_prompt="What felt most unresolved in this moment, and where did you notice even a slight shift?",
                    mixed_feeling_insight=(
                        f"You may have been feeling {', '.join((multimodal_summary.mixed_feelings or text_result.candidate_mixed_feelings)[:2])}."
                    ),
                ),
            ),
            provider="mock",
            model="mock-synthesis",
            prompt_version=PROMPT_VERSION,
            fallback_reason=fallback_reason,
        )
        print(
            "[SYNTHESIS] using mock fallback",
            {
                "fallback_reason": fallback.fallback_reason,
                "clip_summary": fallback.result.clip_evaluation.summary,
                "reflection_prompt": fallback.result.daily_summary_update.reflection_prompt,
            },
        )
        return fallback

    def _build_summary(self, transcript: str, multimodal_summary: MultimodalSummary, labels: list[str]) -> str:
        short = transcript.strip().split(".")[0]
        if len(short) > 108:
            short = f"{short[:105].rstrip()}..."
        feeling = multimodal_summary.dominant_emotions[0] if multimodal_summary.dominant_emotions else (labels[0] if labels else "strained")
        return f"You sounded {feeling} while trying to talk through: {short}"

    def _build_support_suggestion(self, support_style: str, heart_result: HeartAnalysisResult) -> str:
        base = {
            "gentle friend": "Try naming the next small thing instead of the whole pile.",
            "calm coach": "Shrink the moment to one immediate action you can finish.",
            "reflective guide": "Pause long enough to notice what this moment was asking from you.",
        }.get(support_style, "Take one steadying breath and narrow the next step.")
        if heart_result.activation_flag:
            return f"{base} Your body also seemed activated, so slowing down first may help."
        return base

    def _distress_intensity(
        self,
        multimodal_summary: MultimodalSummary,
        heart_result: HeartAnalysisResult,
        tone_result: ToneAnalysisResult,
    ) -> int:
        intensity = heart_result.intensity
        if multimodal_summary.tone_mismatch_present:
            intensity += 1
        if tone_result.delivery_divergence and tone_result.delivery_divergence > 0.5:
            intensity += 1
        if multimodal_summary.dominant_emotions and multimodal_summary.dominant_emotions[0] in {"anxiety", "fear", "anger", "sadness", "grief"}:
            intensity += 1
        return max(1, min(10, intensity))

    def _build_reflection_paragraph(self, multimodal_summary: MultimodalSummary) -> str:
        parts = [
            (
                f"It sounds like this moment carried {' and '.join(multimodal_summary.dominant_emotions[:2])}."
                if multimodal_summary.dominant_emotions
                else "It sounds like this moment carried a lot of emotional weight."
            ),
            multimodal_summary.emotional_arc,
            (
                f"The biggest shift seemed to happen around {round(multimodal_summary.largest_shift.at_seconds)} seconds, "
                f"near '{multimodal_summary.largest_shift.shift_window_text[:80]}'."
                if multimodal_summary.largest_shift.shift_window_text
                else ""
            ),
            (
                "What felt unresolved: the pressure or question underneath the moment still seemed active."
                if multimodal_summary.repeated_triggers
                else "What felt unresolved: some pressure seemed to remain even after naming it."
            ),
        ]
        if multimodal_summary.recovery_detected and multimodal_summary.strongest_recovery_moment:
            parts.append("What helped most: there were signs of a partial recovery once the feeling was put into words.")
        return " ".join(part for part in parts if part)

    def _try_openai_structured_output(
        self,
        input_payload: dict[str, Any],
        multimodal_summary: MultimodalSummary,
        tone_result: ToneAnalysisResult,
        heart_result: HeartAnalysisResult,
        text_result: TextUnderstandingResult,
    ) -> SynthesisExecutionResult | None:
        user_prompt = self._build_user_prompt(
            input_payload=input_payload,
            multimodal_summary=multimodal_summary,
            tone_result=tone_result,
            heart_result=heart_result,
            text_result=text_result,
        )
        print("[SYNTHESIS] openai user prompt", user_prompt)
        try:
            client = OpenAI(api_key=settings.openai_api_key)
            response = client.responses.create(
                model=settings.openai_model,
                store=False,
                input=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "wellness_synthesis",
                        "strict": True,
                        "schema": OPENAI_SYNTHESIS_SCHEMA,
                    }
                },
            )
            content = response.output_text
            print("[SYNTHESIS] openai raw response", content)
            parsed = json.loads(content)
            return SynthesisExecutionResult(
                result=SynthesisResult.model_validate(parsed),
                provider="openai",
                model=settings.openai_model,
                prompt_version=PROMPT_VERSION,
                raw_response_text=content,
            )
        except Exception as exc:
            print("[SYNTHESIS] openai call failed", {"error": str(exc), "model": settings.openai_model})
            return None

    def _build_system_prompt(self) -> str:
        return (
            "You are a non-clinical wellness reflection assistant producing app-ready outputs for a college-student product. "
            "You receive a structured multimodal summary derived from a spoken recording: transcript-based emotion signals, "
            "vocal delivery observations, and heart-rate activation context. Use only the provided signals. "
            "Keep language supportive, reflective, and non-clinical. Do not diagnose, do not overstate certainty, "
            "and do not invent events, feelings, or physiology. Prefer phrases like 'It sounds like...' and "
            "'You may have been feeling...'. If confidence notes are present, hedge or omit those observations. "
            "If heart-rate data was unreliable, do not make heart claims. Do not give advice or recommendations."
        )

    def _build_user_prompt(
        self,
        input_payload: dict[str, Any],
        multimodal_summary: MultimodalSummary,
        tone_result: ToneAnalysisResult,
        heart_result: HeartAnalysisResult,
        text_result: TextUnderstandingResult,
    ) -> str:
        payload = {
            "prompt_version": PROMPT_VERSION,
            "task": "Synthesize one clip evaluation and a daily summary update candidate. The output must follow the JSON schema exactly.",
            "user_context": input_payload.get("user_context", {}),
            "session_context": {
                "timestamp": input_payload["timestamp"].isoformat(),
                "transcript": input_payload["transcript"],
                "support_style": input_payload["support_style"],
                "prior_day_context": input_payload.get("prior_day_context", {}),
            },
            "multimodal_summary": multimodal_summary.model_dump(),
            "processed_signals": {
                "tone_analysis": tone_result.model_dump(),
                "heart_analysis": heart_result.model_dump(),
                "text_understanding": text_result.model_dump(),
            },
            "writing_rules": [
                "Be specific but calm.",
                "Keep summary lines short enough for cards.",
                "Do not use diagnosis or treatment language.",
                "If evidence is weak, stay modest and use softer wording.",
                "Reflection prompts should be open-ended and emotionally safe.",
                "The end_of_day_reflection should read like a short 4-5 sentence reflection grounded in the structured summary.",
            ],
        }
        return json.dumps(payload, default=str)
