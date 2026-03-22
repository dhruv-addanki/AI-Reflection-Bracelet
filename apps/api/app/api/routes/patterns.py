from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.db.repository import Repository
from app.schemas.requests import ApiEnvelope
from app.utils.time import parse_date_or_today, start_of_week

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("/weekly", response_model=ApiEnvelope)
def get_weekly_summary(
    user_id: str,
    week_start: str | None = None,
    repository: Repository = Depends(get_repository),
) -> ApiEnvelope:
    week = start_of_week(parse_date_or_today(week_start))
    return ApiEnvelope(data=repository.get_weekly_summary(user_id, week))


@router.get("/history", response_model=ApiEnvelope)
def list_weekly_summaries(user_id: str, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    return ApiEnvelope(data=repository.list_weekly_summaries_for_user(user_id))
