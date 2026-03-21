from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.db.repository import Repository
from app.db.store import LocalStore
from app.workers.task_queue import InProcessTaskQueue


@lru_cache(maxsize=1)
def get_store() -> LocalStore:
    return LocalStore(settings.local_store_path)


def get_repository() -> Repository:
    store = get_store()
    return Repository(state=store.load(), persist=store.save)


@lru_cache(maxsize=1)
def get_task_queue() -> InProcessTaskQueue:
    return InProcessTaskQueue()
