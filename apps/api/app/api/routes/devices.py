from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repository
from app.db.repository import Repository
from app.schemas.requests import ApiEnvelope, PairMockRequest

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/pair-mock", response_model=ApiEnvelope)
def pair_mock_device(payload: PairMockRequest, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    user = repository.get_user(payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    nickname = payload.nickname or f"{user.name.split()[0]}'s bracelet"
    device = repository.create_device(user_id=payload.user_id, nickname=nickname)
    return ApiEnvelope(data=device)


@router.get("", response_model=ApiEnvelope)
def list_devices(user_id: str, repository: Repository = Depends(get_repository)) -> ApiEnvelope:
    return ApiEnvelope(data=repository.list_devices_for_user(user_id))
