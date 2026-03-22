from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_repository, get_store, get_task_queue
from app.db.repository import Repository
from app.schemas.requests import ApiEnvelope, ProcessSessionPayload, SeedDemoRequest
from app.utils.demo import generate_demo_sessions
from app.utils.time import start_of_week
from app.workers.task_queue import InProcessTaskQueue

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("/demo", response_model=ApiEnvelope)
def seed_demo(
    payload: SeedDemoRequest,
    repository: Repository = Depends(get_repository),
    task_queue: InProcessTaskQueue = Depends(get_task_queue),
) -> ApiEnvelope:
    if payload.reset:
        store = get_store()
        store.reset()
        repository = Repository(state=store.load(), persist=store.save)

    user = repository.create_user(
        name="Maya Chen",
        school_year="Junior",
        goals=["reduce stress", "understand feelings better", "reflect consistently"],
        support_style="calm coach",
        top_stressors=["deadlines", "group projects", "feeling behind"],
    )
    device = repository.create_device(user_id=user.id, nickname="Campus Loop")

    for item in generate_demo_sessions(datetime.utcnow()):
        session = repository.create_raw_session(
            user_id=user.id,
            device_id=device.id,
            timestamp=item["timestamp"],
            audio_url=None,
            transcript_override=str(item["transcript"]),
            avg_hr=float(item["avg_hr"]),
            peak_hr=float(item["peak_hr"]),
            baseline_delta=float(item["baseline_delta"]),
            hr_quality="seeded",
            hr_log=None,
            battery_status=81,
            source_type="mock",
        )
        task_queue.process_session_now(
            payload=ProcessSessionPayload(
                session_id=session.id,
                user_id=user.id,
                device_id=device.id,
                timestamp=item["timestamp"],
                transcript_override=str(item["transcript"]),
                avg_hr=float(item["avg_hr"]),
                peak_hr=float(item["peak_hr"]),
                baseline_delta=float(item["baseline_delta"]),
                hr_quality="seeded",
                battery_status=81,
                source_type="mock",
                tone_preset=str(item["preset"]),
            ),
            repository=repository,
        )

    today = datetime.utcnow().date()
    return ApiEnvelope(
        data={
            "user": repository.get_user(user.id),
            "device": device,
            "daily_summary": repository.get_daily_summary(user.id, today),
            "weekly_summary": repository.get_weekly_summary(user.id, start_of_week(today)),
        }
    )
