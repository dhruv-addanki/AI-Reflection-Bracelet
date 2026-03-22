from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repository
from app.db.repository import Repository
from app.schemas.requests import ApiEnvelope, SaveReflectionRequest
from app.utils.time import parse_date_or_today

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get("/daily", response_model=ApiEnvelope)
def get_daily_summary(user_id: str, date: str | None = None, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    target_date = parse_date_or_today(date)
    return ApiEnvelope(data=repository.get_daily_summary(user_id, target_date))


@router.get("/history", response_model=ApiEnvelope)
def list_daily_summaries(user_id: str, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    return ApiEnvelope(data=repository.list_daily_summaries_for_user(user_id))


@router.post("/reflection", response_model=ApiEnvelope)
def save_daily_reflection(payload: SaveReflectionRequest, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    summary = repository.save_daily_reflection(payload.user_id, parse_date_or_today(payload.date), payload.response.strip())
    if summary is None:
        raise HTTPException(status_code=404, detail="No daily summary found for that date.")
    return ApiEnvelope(data=summary)
