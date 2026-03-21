from __future__ import annotations

from app.db.repository import Repository
from app.schemas.domain import ClipEvaluation
from app.schemas.requests import ProcessSessionPayload
from app.services.pipeline import SessionPipeline


class InProcessTaskQueue:
    """Small queue abstraction so Celery/RQ can replace this later without route rewrites."""

    def __init__(self) -> None:
        self.pipeline = SessionPipeline()

    def process_session_now(self, payload: ProcessSessionPayload, repository: Repository) -> ClipEvaluation:
        return self.pipeline.process(payload=payload, repository=repository)
