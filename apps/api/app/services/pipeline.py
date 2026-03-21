from __future__ import annotations

from uuid import uuid4

from app.db.repository import Repository
from app.schemas.domain import ClipEvaluation
from app.schemas.requests import ProcessSessionPayload
from app.services.aggregation import AggregationService
from app.services.gpt_synthesis import GptSynthesisService
from app.services.heart_analysis import HeartAnalysisService
from app.services.text_understanding import TextUnderstandingService
from app.services.tone_analysis import ToneAnalysisService
from app.services.transcription import TranscriptionService
from app.utils.time import start_of_week


class SessionPipeline:
    def __init__(self) -> None:
        self.transcription = TranscriptionService()
        self.tone = ToneAnalysisService()
        self.heart = HeartAnalysisService()
        self.text = TextUnderstandingService()
        self.synthesis = GptSynthesisService()
        self.aggregation = AggregationService()

    def process(self, payload: ProcessSessionPayload, repository: Repository) -> ClipEvaluation:
        user = repository.get_user(payload.user_id)
        if user is None:
            raise ValueError("User not found")

        print(
            "[PIPELINE] processing session",
            {
                "session_id": payload.session_id,
                "user_id": payload.user_id,
                "device_id": payload.device_id,
                "timestamp": payload.timestamp.isoformat(),
                "audio_path": payload.audio_path,
                "has_transcript_override": bool(payload.transcript_override),
                "tone_preset": payload.tone_preset,
            },
        )

        prior_day_sessions = repository.list_sessions_for_date(payload.user_id, payload.timestamp.date())
        prior_day_evaluations = repository.list_clip_evaluations(session.id for session in prior_day_sessions if session.id != payload.session_id)
        prior_day_context = {
            "prior_entry_count": len(prior_day_evaluations),
            "recent_summaries": [evaluation.one_line_summary for evaluation in prior_day_evaluations[-3:]],
            "recent_trigger_tags": [tag for evaluation in prior_day_evaluations[-3:] for tag in evaluation.trigger_tags[:2]],
            "recent_primary_feelings": [feeling for evaluation in prior_day_evaluations[-3:] for feeling in evaluation.primary_feelings[:2]],
        }
        print("[PIPELINE] prior day context", prior_day_context)

        transcript_result = self.transcription.transcribe_audio(
            audio_path=payload.audio_path,
            transcript_override=payload.transcript_override,
        )
        print("[PIPELINE] transcript result", transcript_result.model_dump())
        tone_result = self.tone.analyze_tone(
            audio_path=payload.audio_path,
            transcript=transcript_result.transcript,
            tone_labels_override=payload.mock_tone_labels,
            tone_preset=payload.tone_preset,
        )
        print("[PIPELINE] tone result", tone_result.model_dump())
        heart_result = self.heart.analyze_heart(
            avg_hr=payload.avg_hr,
            peak_hr=payload.peak_hr,
            baseline_delta=payload.baseline_delta,
            raw_ppg=payload.optional_raw_ppg,
        )
        print("[PIPELINE] heart result", heart_result.model_dump())
        text_result = self.text.analyze_transcript_text(
            transcript=transcript_result.transcript,
            user_context=user.model_dump(),
            prior_context={},
        )
        print("[PIPELINE] text understanding result", text_result.model_dump())
        synthesis_execution = self.synthesis.synthesize_clip_and_daily_update(
            input_payload={
                "timestamp": payload.timestamp,
                "transcript": transcript_result.transcript,
                "support_style": user.support_style,
                "user_context": {
                    "name": user.name,
                    "school_year": user.school_year,
                    "goals": user.goals,
                    "top_stressors": user.top_stressors,
                },
                "prior_day_context": prior_day_context,
            },
            tone_result=tone_result,
            heart_result=heart_result,
            text_result=text_result,
        )
        synthesis_result = synthesis_execution.result
        print(
            "[PIPELINE] synthesis execution",
            {
                "provider": synthesis_execution.provider,
                "model": synthesis_execution.model,
                "prompt_version": synthesis_execution.prompt_version,
                "fallback_reason": synthesis_execution.fallback_reason,
                "clip_summary": synthesis_result.clip_evaluation.summary,
            },
        )

        evaluation = ClipEvaluation(
            id=f"clip_{uuid4().hex[:12]}",
            session_id=payload.session_id,
            transcript=transcript_result.transcript,
            tone_labels=tone_result.primary_labels,
            tone_scores=tone_result.label_scores,
            heart_summary=heart_result.heart_activation_note,
            trigger_tags=synthesis_result.clip_evaluation.trigger_tags,
            mixed_feelings=synthesis_result.clip_evaluation.mixed_feelings,
            distress_intensity=synthesis_result.clip_evaluation.distress_intensity,
            one_line_summary=synthesis_result.clip_evaluation.summary,
            support_suggestion=synthesis_result.clip_evaluation.support_suggestion,
            primary_feelings=synthesis_result.clip_evaluation.primary_feelings,
            self_talk_markers=text_result.self_talk_markers,
            raw_model_outputs_json={
                "transcription": transcript_result.model_dump(),
                "tone_analysis": tone_result.model_dump(),
                "heart_analysis": heart_result.model_dump(),
                "text_understanding": text_result.model_dump(),
                "synthesis": synthesis_result.model_dump(),
                "synthesis_meta": {
                    "provider": synthesis_execution.provider,
                    "model": synthesis_execution.model,
                    "prompt_version": synthesis_execution.prompt_version,
                    "fallback_reason": synthesis_execution.fallback_reason,
                    "raw_response_text": synthesis_execution.raw_response_text,
                },
            },
        )
        print("[PIPELINE] final clip evaluation", evaluation.model_dump())
        repository.upsert_clip_evaluation(evaluation)
        repository.mark_session_processed(payload.session_id)

        day_sessions = repository.list_sessions_for_date(payload.user_id, payload.timestamp.date())
        day_evaluations = repository.list_clip_evaluations(session.id for session in day_sessions)
        daily_summary = self.aggregation.build_daily_summary(
            user_id=payload.user_id,
            target_date=payload.timestamp.date(),
            sessions=day_sessions,
            evaluations=day_evaluations,
        )
        if daily_summary:
            repository.upsert_daily_summary(daily_summary)
            print("[PIPELINE] daily summary", daily_summary.model_dump())

        user_sessions = repository.list_sessions_for_user(payload.user_id)
        week_start = start_of_week(payload.timestamp.date())
        week_sessions = [session for session in user_sessions if start_of_week(session.started_at.date()) == week_start]
        week_evaluations = repository.list_clip_evaluations(session.id for session in week_sessions)
        weekly_summary = self.aggregation.build_weekly_summary(
            user_id=payload.user_id,
            target_date=payload.timestamp.date(),
            sessions=week_sessions,
            evaluations=week_evaluations,
        )
        if weekly_summary:
            repository.upsert_weekly_summary(weekly_summary)
            print("[PIPELINE] weekly summary", weekly_summary.model_dump())

        return evaluation
