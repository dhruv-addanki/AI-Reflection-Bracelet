from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.db.repository import Repository
from app.schemas.requests import ApiEnvelope
from app.utils.time import parse_date_or_today

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get("/daily", response_model=ApiEnvelope)
def get_daily_summary(user_id: str, date: str | None = None, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    target_date = parse_date_or_today(date)
    return ApiEnvelope(data=repository.get_daily_summary(user_id, target_date))
