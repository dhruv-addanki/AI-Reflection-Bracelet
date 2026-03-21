from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from uuid import uuid4

from app.schemas.domain import (
    ClipEvaluation,
    DailySummary,
    DatabaseState,
    Device,
    RawSession,
    SessionDetail,
    UserProfile,
    WeeklyPatternSummary,
)


class Repository:
    def __init__(self, state: DatabaseState, persist: callable) -> None:
        self.state = state
        self.persist = persist

    def _save(self) -> None:
        self.persist(self.state)

    def create_user(
        self,
        name: str,
        school_year: str,
        goals: list[str],
        support_style: str,
        top_stressors: list[str],
    ) -> UserProfile:
        user = UserProfile(
            id=f"user_{uuid4().hex[:12]}",
            name=name,
            school_year=school_year,
            goals=goals,
            support_style=support_style,
            top_stressors=top_stressors,
            created_at=datetime.utcnow(),
        )
        self.state.users.append(user)
        self._save()
        return user

    def get_user(self, user_id: str) -> UserProfile | None:
        return next((user for user in self.state.users if user.id == user_id), None)

    def create_device(self, user_id: str, nickname: str) -> Device:
        device = Device(
            id=f"device_{uuid4().hex[:12]}",
            user_id=user_id,
            nickname=nickname,
            firmware_version="mock-0.1.0",
            linked_at=datetime.utcnow(),
            status="connected",
        )
        self.state.devices.append(device)
        self._save()
        return device

    def list_devices_for_user(self, user_id: str) -> list[Device]:
        return [device for device in self.state.devices if device.user_id == user_id]

    def get_device(self, device_id: str) -> Device | None:
        return next((device for device in self.state.devices if device.id == device_id), None)

    def create_raw_session(
        self,
        user_id: str,
        device_id: str,
        timestamp: datetime,
        audio_url: str | None,
        transcript_override: str | None,
        avg_hr: float | None,
        peak_hr: float | None,
        baseline_delta: float | None,
        hr_quality: str | None,
        battery_status: int | None,
        source_type: str,
    ) -> RawSession:
        session = RawSession(
            id=f"session_{uuid4().hex[:12]}",
            user_id=user_id,
            device_id=device_id,
            started_at=timestamp,
            ended_at=timestamp,
            audio_url=audio_url,
            transcript_override=transcript_override,
            avg_hr=avg_hr,
            peak_hr=peak_hr,
            baseline_delta=baseline_delta,
            hr_quality=hr_quality,
            battery_status=battery_status,
            upload_status="pending",
            source_type=source_type,
        )
        self.state.raw_sessions.append(session)
        self._save()
        return session

    def mark_session_processed(self, session_id: str) -> RawSession | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        session.upload_status = "processed"
        self._save()
        return session

    def get_session(self, session_id: str) -> RawSession | None:
        return next((session for session in self.state.raw_sessions if session.id == session_id), None)

    def list_sessions_for_user(self, user_id: str) -> list[RawSession]:
        return sorted(
            [session for session in self.state.raw_sessions if session.user_id == user_id],
            key=lambda item: item.started_at,
            reverse=True,
        )

    def list_sessions_for_date(self, user_id: str, target_date: date) -> list[RawSession]:
        return [
            session
            for session in self.list_sessions_for_user(user_id)
            if session.started_at.date() == target_date
        ]

    def upsert_clip_evaluation(self, evaluation: ClipEvaluation) -> ClipEvaluation:
        existing_index = next(
            (index for index, item in enumerate(self.state.clip_evaluations) if item.session_id == evaluation.session_id),
            None,
        )
        if existing_index is None:
            self.state.clip_evaluations.append(evaluation)
        else:
            self.state.clip_evaluations[existing_index] = evaluation
        self._save()
        return evaluation

    def get_clip_evaluation(self, session_id: str) -> ClipEvaluation | None:
        return next(
            (evaluation for evaluation in self.state.clip_evaluations if evaluation.session_id == session_id),
            None,
        )

    def list_clip_evaluations(self, session_ids: Iterable[str]) -> list[ClipEvaluation]:
        wanted = set(session_ids)
        return [evaluation for evaluation in self.state.clip_evaluations if evaluation.session_id in wanted]

    def get_session_detail(self, session_id: str) -> SessionDetail | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        return SessionDetail(session=session, evaluation=self.get_clip_evaluation(session_id))

    def upsert_daily_summary(self, summary: DailySummary) -> DailySummary:
        existing_index = next(
            (
                index
                for index, item in enumerate(self.state.daily_summaries)
                if item.user_id == summary.user_id and item.date == summary.date
            ),
            None,
        )
        if existing_index is None:
            self.state.daily_summaries.append(summary)
        else:
            self.state.daily_summaries[existing_index] = summary
        self._save()
        return summary

    def get_daily_summary(self, user_id: str, target_date: date) -> DailySummary | None:
        return next(
            (
                summary
                for summary in self.state.daily_summaries
                if summary.user_id == user_id and summary.date == target_date
            ),
            None,
        )

    def upsert_weekly_summary(self, summary: WeeklyPatternSummary) -> WeeklyPatternSummary:
        existing_index = next(
            (
                index
                for index, item in enumerate(self.state.weekly_pattern_summaries)
                if item.user_id == summary.user_id and item.week_start == summary.week_start
            ),
            None,
        )
        if existing_index is None:
            self.state.weekly_pattern_summaries.append(summary)
        else:
            self.state.weekly_pattern_summaries[existing_index] = summary
        self._save()
        return summary

    def get_weekly_summary(self, user_id: str, week_start: date) -> WeeklyPatternSummary | None:
        return next(
            (
                summary
                for summary in self.state.weekly_pattern_summaries
                if summary.user_id == user_id and summary.week_start == week_start
            ),
            None,
        )
