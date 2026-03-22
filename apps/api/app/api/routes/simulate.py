from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repository, get_task_queue
from app.db.repository import Repository
from app.schemas.requests import ApiEnvelope, ProcessSessionPayload, SimulateSessionRequest
from app.workers.task_queue import InProcessTaskQueue

router = APIRouter(prefix="/simulate", tags=["simulate"])


@router.post("/session", response_model=ApiEnvelope)
def simulate_session(
    payload: SimulateSessionRequest,
    repository: Repository = Depends(get_repository),
    task_queue: InProcessTaskQueue = Depends(get_task_queue),
) -> ApiEnvelope:
    user = repository.get_user(payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    device_id = payload.device_id
    if device_id is None:
        devices = repository.list_devices_for_user(payload.user_id)
        if not devices:
            raise HTTPException(status_code=400, detail="No paired device found")
        device_id = devices[0].id
    elif repository.get_device(device_id) is None:
        raise HTTPException(status_code=404, detail="Device not found")

    timestamp = payload.timestamp or datetime.utcnow()
    session = repository.create_raw_session(
        user_id=payload.user_id,
        device_id=device_id,
        timestamp=timestamp,
        audio_url=payload.audio_file_url,
        transcript_override=payload.transcript_override,
        avg_hr=payload.avg_hr,
        peak_hr=payload.peak_hr,
        baseline_delta=payload.baseline_delta,
        hr_quality="simulated",
        hr_log=payload.hr_log,
        battery_status=payload.battery_status or 72,
        source_type="mock",
    )
    try:
        evaluation = task_queue.process_session_now(
            payload=ProcessSessionPayload(
                session_id=session.id,
                user_id=payload.user_id,
                device_id=device_id,
                timestamp=timestamp,
                transcript_override=payload.transcript_override,
                avg_hr=payload.avg_hr,
                peak_hr=payload.peak_hr,
                baseline_delta=payload.baseline_delta,
                hr_log=payload.hr_log,
                battery_status=payload.battery_status or 72,
                source_type="mock",
                tone_preset=payload.tone_preset,
                mock_tone_labels=payload.tone_labels,
                audio_file_url=payload.audio_file_url,
            ),
            repository=repository,
        )
    except ValueError as exc:
        repository.mark_session_failed(session.id)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiEnvelope(data={"session": session, "evaluation": evaluation})
