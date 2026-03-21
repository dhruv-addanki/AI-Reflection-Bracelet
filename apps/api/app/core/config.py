from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency installed in runtime environments
    load_dotenv = None

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if load_dotenv is not None:
    load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Reflection Bracelet API"
    api_prefix: str = ""
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")
    openai_transcription_model: str = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_anon_key: str | None = os.getenv("SUPABASE_ANON_KEY")
    database_url: str | None = os.getenv("DATABASE_URL")
    local_store_path: Path = Path(__file__).resolve().parents[2] / "data" / "local_store.json"
    allow_cors_origin: str = os.getenv("ALLOW_CORS_ORIGIN", "*")


settings = Settings()
