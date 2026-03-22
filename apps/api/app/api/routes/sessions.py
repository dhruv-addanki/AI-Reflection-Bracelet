from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.api.deps import get_repository, get_task_queue
from app.db.repository import Repository
from app.schemas.requests import ApiEnvelope, ProcessSessionPayload, SessionUploadJsonRequest
from app.workers.task_queue import InProcessTaskQueue

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/upload", response_model=ApiEnvelope)
async def upload_session(
    request: Request,
    audio_file: UploadFile | None = File(default=None),
    repository: Repository = Depends(get_repository),
    task_queue: InProcessTaskQueue = Depends(get_task_queue),
) -> ApiEnvelope:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = SessionUploadJsonRequest.model_validate(await request.json())
        saved_audio_path = None
    else:
        form = await request.form()
        data = SessionUploadJsonRequest(
            user_id=str(form.get("user_id")),
            device_id=str(form.get("device_id")),
            timestamp=str(form.get("timestamp")),
            audio_file_url=form.get("audio_file_url"),
            transcript_override=form.get("transcript_override"),
            avg_hr=_parse_float(form.get("avg_hr")),
            peak_hr=_parse_float(form.get("peak_hr")),
            baseline_delta=_parse_float(form.get("baseline_delta")),
            hr_quality=form.get("hr_quality"),
            hr_log=_parse_list(form.get("hr_log")),
            battery_status=_parse_int(form.get("battery_status")),
            optional_raw_ppg=_parse_list(form.get("optional_raw_ppg")),
            source_type=str(form.get("source_type") or "mock"),
            mock_tone_labels=_parse_list(form.get("mock_tone_labels")),
            tone_preset=form.get("tone_preset"),
        )
        saved_audio_path = await _persist_upload(audio_file)

    if repository.get_user(data.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    if repository.get_device(data.device_id) is None:
        raise HTTPException(status_code=404, detail="Device not found")

    session = repository.create_raw_session(
        user_id=data.user_id,
        device_id=data.device_id,
        timestamp=data.timestamp,
        audio_url=data.audio_file_url,
        transcript_override=data.transcript_override,
        avg_hr=data.avg_hr,
        peak_hr=data.peak_hr,
        baseline_delta=data.baseline_delta,
        hr_quality=data.hr_quality,
        hr_log=data.hr_log,
        battery_status=data.battery_status,
        source_type=data.source_type,
    )
    try:
        evaluation = task_queue.process_session_now(
            payload=ProcessSessionPayload(
                session_id=session.id,
                user_id=data.user_id,
                device_id=data.device_id,
                timestamp=data.timestamp,
                audio_path=saved_audio_path,
                audio_file_url=data.audio_file_url,
                transcript_override=data.transcript_override,
                avg_hr=data.avg_hr,
                peak_hr=data.peak_hr,
                baseline_delta=data.baseline_delta,
                hr_quality=data.hr_quality,
                hr_log=data.hr_log,
                battery_status=data.battery_status,
                optional_raw_ppg=data.optional_raw_ppg,
                source_type=data.source_type,
                mock_tone_labels=data.mock_tone_labels,
                tone_preset=data.tone_preset,
            ),
            repository=repository,
        )
    except ValueError as exc:
        repository.mark_session_failed(session.id)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        repository.mark_session_failed(session.id)
        raise HTTPException(status_code=500, detail=f"Session processing failed: {exc}") from exc
    return ApiEnvelope(data={"session": session.model_dump(), "evaluation": evaluation.model_dump()})


@router.get("/today", response_model=ApiEnvelope)
def list_today_sessions(user_id: str, date: str | None = None, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    from app.utils.time import parse_date_or_today

    target_date = parse_date_or_today(date)
    sessions = repository.list_sessions_for_date(user_id, target_date)
    evaluations = {evaluation.session_id: evaluation for evaluation in repository.list_clip_evaluations(session.id for session in sessions)}
    data = [
        {
            "session": session.model_dump(),
            "evaluation": evaluations.get(session.id).model_dump() if evaluations.get(session.id) is not None else None,
        }
        for session in sorted(sessions, key=lambda item: item.started_at, reverse=True)
    ]
    return ApiEnvelope(data=data)


@router.get("/{session_id}", response_model=ApiEnvelope)
def get_session(session_id: str, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    detail = repository.get_session_detail(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return ApiEnvelope(data=detail.model_dump())


def _parse_float(value: object) -> float | None:
    return float(value) if value not in (None, "", "null") else None


def _parse_int(value: object) -> int | None:
    return int(value) if value not in (None, "", "null") else None


def _parse_list(value: object) -> list[str] | list[float] | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]
    return None


async def _persist_upload(audio_file: UploadFile | None) -> str | None:
    if audio_file is None:
        return None
    uploads_dir = Path(__file__).resolve().parents[3] / "data" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    target = uploads_dir / audio_file.filename
    target.write_bytes(await audio_file.read())
    return str(target)
