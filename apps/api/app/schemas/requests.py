from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    name: str
    school_year: str
    goals: list[str]
    support_style: str
    top_stressors: list[str]


class PairMockRequest(BaseModel):
    user_id: str
    nickname: str | None = None


class SessionUploadJsonRequest(BaseModel):
    user_id: str
    device_id: str
    timestamp: datetime
    audio_file_url: str | None = None
    transcript_override: str | None = None
    avg_hr: float | None = None
    peak_hr: float | None = None
    baseline_delta: float | None = None
    hr_quality: str | None = None
    hr_log: list[dict[str, Any]] | None = None
    battery_status: int | None = None
    optional_raw_ppg: list[float] | None = None
    source_type: Literal["mock", "bracelet"] = "mock"
    mock_tone_labels: list[str] | None = None
    tone_preset: str | None = None


class SimulateSessionRequest(BaseModel):
    user_id: str
    device_id: str | None = None
    timestamp: datetime | None = None
    transcript_override: str | None = None
    tone_preset: str | None = None
    tone_labels: list[str] | None = None
    avg_hr: float | None = None
    peak_hr: float | None = None
    baseline_delta: float | None = None
    hr_log: list[dict[str, Any]] | None = None
    battery_status: int | None = None
    audio_file_url: str | None = None


class SeedDemoRequest(BaseModel):
    reset: bool = Field(default=True)


class ProcessSessionPayload(BaseModel):
    session_id: str
    user_id: str
    device_id: str
    timestamp: datetime
    audio_path: str | None = None
    audio_file_url: str | None = None
    transcript_override: str | None = None
    avg_hr: float | None = None
    peak_hr: float | None = None
    baseline_delta: float | None = None
    hr_quality: str | None = None
    hr_log: list[dict[str, Any]] | None = None
    battery_status: int | None = None
    optional_raw_ppg: list[float] | None = None
    source_type: Literal["mock", "bracelet"] = "mock"
    mock_tone_labels: list[str] | None = None
    tone_preset: str | None = None


class ApiEnvelope(BaseModel):
    ok: bool = True
    data: Any
