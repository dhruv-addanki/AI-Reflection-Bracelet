from __future__ import annotations

from collections import Counter
from datetime import date
from uuid import uuid4

from app.schemas.domain import ClipEvaluation, DailySummary, RawSession, TimelineBlock, WeeklyPatternSummary
from app.utils.time import format_time_window, start_of_week


class AggregationService:
    def build_daily_summary(
        self,
        user_id: str,
        target_date: date,
        sessions: list[RawSession],
        evaluations: list[ClipEvaluation],
    ) -> DailySummary | None:
        if not sessions or not evaluations:
            return None

        evaluations_by_session = {evaluation.session_id: evaluation for evaluation in evaluations}
        enriched = [
            (session, evaluations_by_session[session.id])
            for session in sorted(sessions, key=lambda item: item.started_at)
            if session.id in evaluations_by_session
        ]
        if not enriched:
            return None

        highest = max(enriched, key=lambda item: item[1].distress_intensity)
        calmest = min(enriched, key=lambda item: item[1].distress_intensity)

        repeated_feeling = Counter(
            feeling
            for _, evaluation in enriched
            for feeling in evaluation.primary_feelings
        ).most_common(1)[0][0]

        timeline = [
            TimelineBlock(
                label=format_time_window(session.started_at),
                time_range=session.started_at.strftime("%-I:%M %p"),
                feeling=(evaluation.primary_feelings[0] if evaluation.primary_feelings else "reflective"),
                intensity=max(1, min(10, evaluation.distress_intensity)),
            )
            for session, evaluation in enriched
        ]

        mixed = []
        for _, evaluation in enriched:
            mixed.extend(evaluation.mixed_feelings)

        v2_summaries = [
            evaluation.raw_model_outputs_json.get("pipeline_v2", {}).get("multimodal_summary", {})
            for _, evaluation in enriched
        ]
        repeated_triggers = [
            trigger
            for summary in v2_summaries
            for trigger in summary.get("repeated_triggers", [])
        ]
        mixed_insight = (
            f"You may have been feeling {mixed[0]}."
            if mixed
            else "More than one feeling seemed present across the day."
        )

        return DailySummary(
            id=f"daily_{uuid4().hex[:12]}",
            user_id=user_id,
            date=target_date,
            emotional_recap="It sounds like today moved between pressure, effort, and small moments of release.",
            hardest_moment=highest[1].one_line_summary,
            calmest_moment=calmest[1].one_line_summary,
            repeated_feeling=repeated_feeling,
            one_thing_to_notice=(
                f"A recurring theme seems to be {(repeated_triggers[0] if repeated_triggers else (highest[1].trigger_tags[0] if highest[1].trigger_tags else 'stress building early'))}."
            ),
            mood_timeline_json=timeline,
            recap_paragraph=next(
                (
                    summary.get("emotional_arc")
                    for summary in v2_summaries
                    if summary.get("emotional_arc")
                ),
                "Your day seems to have carried a steady undercurrent of strain, especially around demands that felt stacked. Still, there were signs that venting, stepping away, or naming the feeling gave you a little more room.",
            ),
            reflection_prompt="When you started feeling overloaded, what helped you feel even slightly more grounded?",
            mixed_feeling_insight=mixed_insight,
        )

    def build_weekly_summary(
        self,
        user_id: str,
        target_date: date,
        sessions: list[RawSession],
        evaluations: list[ClipEvaluation],
    ) -> WeeklyPatternSummary | None:
        if not sessions or not evaluations:
            return None

        evaluations_by_session = {evaluation.session_id: evaluation for evaluation in evaluations}
        time_windows = Counter()
        triggers = Counter()
        self_talk = Counter()
        supports = Counter()

        for session in sessions:
            evaluation = evaluations_by_session.get(session.id)
            if not evaluation:
                continue
            v2_summary = evaluation.raw_model_outputs_json.get("pipeline_v2", {}).get("multimodal_summary", {})
            time_windows[format_time_window(session.started_at)] += 1
            for item in (v2_summary.get("repeated_triggers") or evaluation.trigger_tags):
                triggers[item] += 1
            for item in evaluation.self_talk_markers:
                self_talk[item] += 1
            supports[evaluation.support_suggestion] += 1

        return WeeklyPatternSummary(
            id=f"weekly_{uuid4().hex[:12]}",
            user_id=user_id,
            week_start=start_of_week(target_date),
            top_triggers=[item for item, _ in triggers.most_common(3)] or ["general overload"],
            hardest_time_windows=[item for item, _ in time_windows.most_common(3)] or ["Afternoon"],
            repeated_self_talk_patterns=[item for item, _ in self_talk.most_common(3)] or ["trying to stay afloat"],
            support_strategies_that_help=[item for item, _ in supports.most_common(3)] or ["Take one steadying breath and narrow the next step."],
            weekly_reflection=(
                f"A recurring theme seems to be {next(iter(triggers), 'pressure building around academics and time')}. "
                "The moments that soften most appear to be the ones where you pause, vent safely, or reduce the problem to one step."
            ),
        )
