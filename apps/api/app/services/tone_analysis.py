from __future__ import annotations

from app.schemas.domain import ToneAnalysisResult


PRESET_TONES: dict[str, tuple[list[str], float, str, str]] = {
    "overwhelmed": (["overwhelmed", "tense"], 0.82, "high", "Speech would likely sound compressed and urgent."),
    "calm but tired": (["tired", "steady"], 0.68, "low", "Lower energy delivery with slower pacing."),
    "frustrated": (["frustrated", "activated"], 0.79, "high", "Sharper emphasis and quicker phrase endings."),
    "emotionally released": (["relieved", "drained"], 0.71, "medium", "Looser pacing after an earlier stress peak."),
    "anxious": (["anxious", "restless"], 0.84, "high", "Slightly clipped phrasing with anxious activation."),
}


class ToneAnalysisService:
    def analyze_tone(
        self,
        audio_path: str | None,
        transcript: str | None = None,
        tone_labels_override: list[str] | None = None,
        tone_preset: str | None = None,
    ) -> ToneAnalysisResult:
        if tone_labels_override:
            scores = [
                {"label": label, "score": round(0.74 - index * 0.08, 2)}
                for index, label in enumerate(tone_labels_override)
            ]
            return ToneAnalysisResult(
                primary_labels=tone_labels_override,
                label_scores=scores,
                arousal_level="medium",
                confidence=0.72,
                acoustic_features_summary="Tone labels were provided by the simulator.",
            )

        if tone_preset and tone_preset in PRESET_TONES:
            labels, confidence, arousal, acoustic = PRESET_TONES[tone_preset]
            return ToneAnalysisResult(
                primary_labels=labels,
                label_scores=[{"label": label, "score": round(confidence - index * 0.09, 2)} for index, label in enumerate(labels)],
                arousal_level=arousal,
                confidence=confidence,
                acoustic_features_summary=acoustic,
            )

        transcript_text = (transcript or "").lower()
        if any(token in transcript_text for token in ["behind", "deadline", "too much"]):
            labels = ["overwhelmed", "strained"]
            arousal = "high"
        elif any(token in transcript_text for token in ["proud", "steady", "walk"]):
            labels = ["relieved", "tired"]
            arousal = "low"
        else:
            labels = ["reflective", "tense"]
            arousal = "medium"

        return ToneAnalysisResult(
            primary_labels=labels,
            label_scores=[{"label": label, "score": round(0.7 - index * 0.12, 2)} for index, label in enumerate(labels)],
            arousal_level=arousal,
            confidence=0.66,
            acoustic_features_summary="Generated from transcript cues while hardware audio analysis is stubbed.",
        )
