from __future__ import annotations

from pathlib import Path
from threading import Lock

from app.core.config import settings

try:
    from huggingface_hub import snapshot_download
except ImportError:  # pragma: no cover - optional runtime dependency
    snapshot_download = None  # type: ignore[assignment]

try:
    from speechbrain.inference.classifiers import EncoderClassifier
except ImportError:  # pragma: no cover - optional runtime dependency
    EncoderClassifier = None  # type: ignore[assignment]

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
except ImportError:  # pragma: no cover - optional runtime dependency
    AutoModelForSequenceClassification = None  # type: ignore[assignment]
    AutoTokenizer = None  # type: ignore[assignment]
    pipeline = None  # type: ignore[assignment]


GO_EMOTIONS_MODEL = "SamLowe/roberta-base-go_emotions"
TRIGGER_MODEL = "cross-encoder/nli-deberta-v3-small"
SER_MODEL = "speechbrain/emotion-recognition-wav2vec2-IEMOCAP"


class ReflectModelManager:
    _go_emotions = None
    _zero_shot = None
    _ser = None
    _lock = Lock()

    def __init__(self) -> None:
        self.cache_dir = settings.model_cache_dir / "huggingface"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hub_dir = self.cache_dir / "hub"

    def get_go_emotions(self):
        if pipeline is None or snapshot_download is None:  # pragma: no cover - dependency issue
            return None
        if ReflectModelManager._go_emotions is None:
            with ReflectModelManager._lock:
                if ReflectModelManager._go_emotions is None:
                    if AutoModelForSequenceClassification is None or AutoTokenizer is None:
                        return None
                    local_path = self._resolve_local_snapshot(GO_EMOTIONS_MODEL)
                    model = AutoModelForSequenceClassification.from_pretrained(
                        str(local_path),
                        local_files_only=True,
                    )
                    tokenizer = AutoTokenizer.from_pretrained(
                        str(local_path),
                        local_files_only=True,
                    )
                    ReflectModelManager._go_emotions = pipeline(
                        "text-classification",
                        model=model,
                        tokenizer=tokenizer,
                        top_k=None,
                        device=-1,
                    )
        return ReflectModelManager._go_emotions

    def get_zero_shot(self):
        if pipeline is None or snapshot_download is None:  # pragma: no cover - dependency issue
            return None
        if ReflectModelManager._zero_shot is None:
            with ReflectModelManager._lock:
                if ReflectModelManager._zero_shot is None:
                    if AutoModelForSequenceClassification is None or AutoTokenizer is None:
                        return None
                    local_path = self._resolve_local_snapshot(TRIGGER_MODEL)
                    model = AutoModelForSequenceClassification.from_pretrained(
                        str(local_path),
                        local_files_only=True,
                    )
                    tokenizer = AutoTokenizer.from_pretrained(
                        str(local_path),
                        local_files_only=True,
                    )
                    ReflectModelManager._zero_shot = pipeline(
                        "zero-shot-classification",
                        model=model,
                        tokenizer=tokenizer,
                        device=-1,
                    )
        return ReflectModelManager._zero_shot

    def get_ser(self):
        if EncoderClassifier is None:  # pragma: no cover - dependency issue
            return None
        if ReflectModelManager._ser is None:
            with ReflectModelManager._lock:
                if ReflectModelManager._ser is None:
                    savedir = Path(settings.model_cache_dir) / "speechbrain-ser"
                    savedir.mkdir(parents=True, exist_ok=True)
                    try:
                        ReflectModelManager._ser = EncoderClassifier.from_hparams(
                            source=SER_MODEL,
                            savedir=str(savedir),
                            run_opts={"device": "cpu"},
                            huggingface_cache_dir=str(self.cache_dir),
                        )
                    except Exception as exc:  # pragma: no cover - runtime dependency mismatch
                        print("[MODEL_MANAGER] SER unavailable", {"model": SER_MODEL, "error": str(exc)})
                        ReflectModelManager._ser = False
        return ReflectModelManager._ser if ReflectModelManager._ser is not False else None

    def _resolve_local_snapshot(self, repo_id: str) -> Path:
        sanitized = repo_id.replace("/", "--")
        snapshots_root = self.hub_dir / f"models--{sanitized}" / "snapshots"
        if snapshots_root.exists():
            snapshot_dirs = sorted(path for path in snapshots_root.iterdir() if path.is_dir())
            if snapshot_dirs:
                return snapshot_dirs[-1]
        if snapshot_download is None:  # pragma: no cover - dependency issue
            raise FileNotFoundError(f"Model snapshot for {repo_id} was not found in the local cache.")
        resolved = snapshot_download(repo_id, cache_dir=str(self.cache_dir), local_files_only=True)
        return Path(resolved)
