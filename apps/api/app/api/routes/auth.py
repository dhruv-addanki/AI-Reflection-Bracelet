from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repository
from app.db.repository import Repository
from app.schemas.requests import ApiEnvelope, OnboardingRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/onboarding", response_model=ApiEnvelope)
def create_user(payload: OnboardingRequest, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    user = repository.create_user(
        name=payload.name,
        school_year=payload.school_year,
        goals=payload.goals,
        support_style=payload.support_style,
        top_stressors=payload.top_stressors,
    )
    return ApiEnvelope(data=user)


@router.get("/profile/{user_id}", response_model=ApiEnvelope)
def get_profile(user_id: str, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    user = repository.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ApiEnvelope(data=user)
