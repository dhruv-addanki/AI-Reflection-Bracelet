from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.requests import ApiEnvelope, BraceletTestUploadRequest

router = APIRouter(tags=["bracelet"])


@router.post("/test-upload", response_model=ApiEnvelope)
def test_upload(payload: BraceletTestUploadRequest) -> ApiEnvelope:
    log_payload = payload.model_dump()
    print("[BRACELET] test upload", log_payload)
    return ApiEnvelope(
        data={
            "received": log_payload,
            "ok": True,
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Bracelet connectivity test received.",
        }
    )
