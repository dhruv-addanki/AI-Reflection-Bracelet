from __future__ import annotations

import json
from pathlib import Path

from app.schemas.domain import DatabaseState


class LocalStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> DatabaseState:
        if not self.path.exists():
            return DatabaseState()
        payload = json.loads(self.path.read_text())
        return DatabaseState.model_validate(payload)

    def save(self, state: DatabaseState) -> None:
        self.path.write_text(state.model_dump_json(indent=2))

    def reset(self) -> DatabaseState:
        state = DatabaseState()
        self.save(state)
        return state
