from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    id: str
    name: str
    school_year: str
    goals: list[str]
    support_style: str
    top_stressors: list[str]
    created_at: datetime


class Device(BaseModel):
    id: str
    user_id: str
    nickname: str
    firmware_version: str
    linked_at: datetime
    status: Literal["connected", "idle", "needs-charge"]


class RawSession(BaseModel):
    id: str
    user_id: str
    device_id: str
    started_at: datetime
    ended_at: datetime
    audio_url: str | None = None
    transcript_override: str | None = None
    avg_hr: float | None = None
    peak_hr: float | None = None
    baseline_delta: float | None = None
    hr_quality: str | None = None
    battery_status: int | None = None
    upload_status: Literal["pending", "processed", "failed"]
    source_type: Literal["mock", "bracelet"]


class ClipEvaluation(BaseModel):
    id: str
    session_id: str
    transcript: str
    tone_labels: list[str]
    tone_scores: list[dict[str, Any]]
    heart_summary: str
    trigger_tags: list[str]
    mixed_feelings: list[str]
    distress_intensity: int
    one_line_summary: str
    support_suggestion: str
    primary_feelings: list[str]
    self_talk_markers: list[str]
    raw_model_outputs_json: dict[str, Any]


class TimelineBlock(BaseModel):
    label: str
    time_range: str
    feeling: str
    intensity: int = Field(ge=1, le=10)


class DailySummary(BaseModel):
    id: str
    user_id: str
    date: date
    emotional_recap: str
    hardest_moment: str
    calmest_moment: str
    repeated_feeling: str
    one_thing_to_notice: str
    mood_timeline_json: list[TimelineBlock]
    recap_paragraph: str
    reflection_prompt: str
    mixed_feeling_insight: str


class WeeklyPatternSummary(BaseModel):
    id: str
    user_id: str
    week_start: date
    top_triggers: list[str]
    hardest_time_windows: list[str]
    repeated_self_talk_patterns: list[str]
    support_strategies_that_help: list[str]
    weekly_reflection: str


class TranscriptResult(BaseModel):
    transcript: str
    source: str


class ToneAnalysisResult(BaseModel):
    primary_labels: list[str]
    label_scores: list[dict[str, Any]]
    arousal_level: str
    confidence: float
    acoustic_features_summary: str


class HeartAnalysisResult(BaseModel):
    heart_activation_note: str
    activation_flag: bool
    intensity: int
    quality_note: str


class TextUnderstandingResult(BaseModel):
    themes: list[str]
    trigger_tags: list[str]
    self_talk_markers: list[str]
    repeated_concerns: list[str]
    candidate_mixed_feelings: list[str]


class SynthesisClipEvaluation(BaseModel):
    summary: str
    primary_feelings: list[str]
    mixed_feelings: list[str]
    trigger_tags: list[str]
    heart_activation_note: str
    support_suggestion: str
    distress_intensity: int


class SynthesisDailyUpdate(BaseModel):
    hardest_moment: str
    calmest_moment: str
    most_repeated_feeling: str
    one_thing_to_notice: str
    timeline_blocks: list[TimelineBlock]
    end_of_day_reflection: str
    reflection_prompt: str
    mixed_feeling_insight: str


class SynthesisResult(BaseModel):
    clip_evaluation: SynthesisClipEvaluation
    daily_summary_update: SynthesisDailyUpdate


class SessionDetail(BaseModel):
    session: RawSession
    evaluation: ClipEvaluation | None = None


class DatabaseState(BaseModel):
    users: list[UserProfile] = Field(default_factory=list)
    devices: list[Device] = Field(default_factory=list)
    raw_sessions: list[RawSession] = Field(default_factory=list)
    clip_evaluations: list[ClipEvaluation] = Field(default_factory=list)
    daily_summaries: list[DailySummary] = Field(default_factory=list)
    weekly_pattern_summaries: list[WeeklyPatternSummary] = Field(default_factory=list)
