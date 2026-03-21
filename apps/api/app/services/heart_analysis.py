from __future__ import annotations

from app.schemas.domain import HeartAnalysisResult


class HeartAnalysisService:
    def analyze_heart(
        self,
        avg_hr: float | None,
        peak_hr: float | None,
        baseline_delta: float | None,
        raw_ppg: list[float] | None = None,
    ) -> HeartAnalysisResult:
        avg = avg_hr or 0
        peak = peak_hr or avg
        delta = baseline_delta or 0

        if peak >= 115 or delta >= 18:
            return HeartAnalysisResult(
                heart_activation_note="Your body seemed noticeably activated during this moment.",
                activation_flag=True,
                intensity=8,
                quality_note="Elevated peak heart rate relative to baseline.",
            )
        if peak >= 95 or delta >= 8:
            return HeartAnalysisResult(
                heart_activation_note="There are signs of moderate stress activation here.",
                activation_flag=True,
                intensity=5,
                quality_note="Mild elevation above baseline.",
            )
        return HeartAnalysisResult(
            heart_activation_note="Heart data looks fairly steady in this clip.",
            activation_flag=False,
            intensity=2,
            quality_note="Low activation or limited usable heart signal.",
        )
