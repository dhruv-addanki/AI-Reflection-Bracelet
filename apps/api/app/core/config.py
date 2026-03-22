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

DEFAULT_MODEL_CACHE_DIR = Path(os.getenv("MODEL_CACHE_DIR", Path(__file__).resolve().parents[2] / ".model-cache"))
os.environ.setdefault("MODEL_CACHE_DIR", str(DEFAULT_MODEL_CACHE_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(DEFAULT_MODEL_CACHE_DIR))
os.environ.setdefault("HF_HOME", str(DEFAULT_MODEL_CACHE_DIR / "huggingface"))


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Reflection Bracelet API"
    api_prefix: str = ""
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")
    openai_transcription_model: str = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    model_cache_dir: Path = DEFAULT_MODEL_CACHE_DIR
    reflect_pipeline_enabled: bool = os.getenv("REFLECT_PIPELINE_ENABLED", "true").lower() == "true"
    reflect_goemotions_threshold: float = float(os.getenv("REFLECT_GOEMOTIONS_THRESHOLD", "0.30"))
    reflect_ser_workers: int = int(os.getenv("REFLECT_SER_WORKERS", "4"))
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_anon_key: str | None = os.getenv("SUPABASE_ANON_KEY")
    database_url: str | None = os.getenv("DATABASE_URL")
    local_store_path: Path = Path(__file__).resolve().parents[2] / "data" / "local_store.json"
    allow_cors_origin: str = os.getenv("ALLOW_CORS_ORIGIN", "*")


settings = Settings()
