from __future__ import annotations

from pathlib import Path
from threading import Lock

from app.core.config import settings

try:
    from huggingface_hub import snapshot_download
except ImportError:  # pragma: no cover - optional runtime dependency
    snapshot_download = None  # type: ignore[assignment]

try:
    import transformers
    from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer, pipeline
except ImportError:  # pragma: no cover - optional runtime dependency
    transformers = None  # type: ignore[assignment]
    AutoModel = None  # type: ignore[assignment]
    AutoModelForSequenceClassification = None  # type: ignore[assignment]
    AutoTokenizer = None  # type: ignore[assignment]
    pipeline = None  # type: ignore[assignment]

if transformers is not None and not hasattr(transformers, "AutoModelWithLMHead"):
    transformers.AutoModelWithLMHead = transformers.AutoModel

try:
    import torch
except ImportError:  # pragma: no cover - optional runtime dependency
    torch = None  # type: ignore[assignment]


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
        if torch is None or AutoModel is None:  # pragma: no cover - dependency issue
            return None
        if ReflectModelManager._ser is None:
            with ReflectModelManager._lock:
                if ReflectModelManager._ser is None:
                    try:
                        ser_snapshot = self._resolve_local_snapshot(SER_MODEL)
                        base_wav2vec_snapshot = self._resolve_local_snapshot_optional("facebook/wav2vec2-base")
                        if base_wav2vec_snapshot is None:
                            raise FileNotFoundError("facebook/wav2vec2-base snapshot not found in local cache.")
                        ReflectModelManager._ser = LocalSerEmotionClassifier(
                            base_model_path=base_wav2vec_snapshot,
                            ser_snapshot_path=ser_snapshot,
                        )
                    except Exception as exc:  # pragma: no cover - runtime dependency mismatch
                        print("[MODEL_MANAGER] SER unavailable", {"model": SER_MODEL, "error": str(exc)})
                        ReflectModelManager._ser = False
        return ReflectModelManager._ser if ReflectModelManager._ser is not False else None

    def _resolve_local_snapshot(self, repo_id: str) -> Path:
        sanitized = repo_id.replace("/", "--")
        candidate_roots = [
            self.hub_dir / f"models--{sanitized}" / "snapshots",
            self.cache_dir / f"models--{sanitized}" / "snapshots",
        ]
        for snapshots_root in candidate_roots:
            if snapshots_root.exists():
                snapshot_dirs = sorted(path for path in snapshots_root.iterdir() if path.is_dir())
                if snapshot_dirs:
                    return snapshot_dirs[-1]
        if snapshot_download is None:  # pragma: no cover - dependency issue
            raise FileNotFoundError(f"Model snapshot for {repo_id} was not found in the local cache.")
        resolved = snapshot_download(repo_id, cache_dir=str(self.cache_dir), local_files_only=True)
        return Path(resolved)

    def _resolve_local_snapshot_optional(self, repo_id: str) -> Path | None:
        try:
            return self._resolve_local_snapshot(repo_id)
        except Exception:
            return None


class LocalSerEmotionClassifier:
    def __init__(self, base_model_path: Path, ser_snapshot_path: Path) -> None:
        if torch is None or AutoModel is None:  # pragma: no cover - dependency issue
            raise RuntimeError("Torch/transformers are unavailable for SER.")
        self.device = "cpu"
        self.encoder = AutoModel.from_pretrained(str(base_model_path), local_files_only=True)
        wav2vec_state = torch.load(ser_snapshot_path / "wav2vec2.ckpt", map_location="cpu")
        cleaned_state = {
            key.removeprefix("model."): value
            for key, value in wav2vec_state.items()
            if key.startswith("model.")
        }
        self.encoder.load_state_dict(cleaned_state, strict=False)
        self.encoder.eval()

        head_state = torch.load(ser_snapshot_path / "model.ckpt", map_location="cpu")
        weight = head_state["0.w.weight"]
        self.classifier = torch.nn.Linear(weight.shape[1], weight.shape[0], bias=False)
        self.classifier.weight.data.copy_(weight)
        self.classifier.eval()

        self.labels = self._load_labels(ser_snapshot_path / "label_encoder.txt")

    def classify_batch(self, wavs, wav_lens=None):
        if torch is None:  # pragma: no cover - dependency issue
            raise RuntimeError("Torch is unavailable for SER.")
        if len(wavs.shape) == 1:
            wavs = wavs.unsqueeze(0)
        wavs = wavs.float()
        attention_mask = None
        if wav_lens is not None:
            max_length = wavs.shape[1]
            lengths = torch.clamp((wav_lens * max_length).long(), min=1, max=max_length)
            attention_mask = torch.arange(max_length).unsqueeze(0) < lengths.unsqueeze(1)
            attention_mask = attention_mask.long()
        with torch.no_grad():
            outputs = self.encoder(input_values=wavs, attention_mask=attention_mask)
            hidden = outputs.last_hidden_state
            if attention_mask is not None:
                mask = attention_mask.unsqueeze(-1).to(hidden.dtype)
                pooled = (hidden * mask).sum(dim=1) / torch.clamp(mask.sum(dim=1), min=1.0)
            else:
                pooled = hidden.mean(dim=1)
            logits = self.classifier(pooled)
            probs = torch.softmax(logits, dim=-1)
            score, index = torch.max(probs, dim=-1)
            labels = [self.labels[int(item)] for item in index.tolist()]
            return probs, score, index, labels

    def _load_labels(self, path: Path) -> list[str]:
        labels: dict[int, str] = {}
        for line in path.read_text().splitlines():
            if "=>" not in line or line.startswith("="):
                continue
            raw_label, raw_index = [part.strip() for part in line.split("=>", 1)]
            if raw_label.startswith("'") and raw_label.endswith("'"):
                raw_label = raw_label[1:-1]
            labels[int(raw_index)] = raw_label
        return [labels[index] for index in sorted(labels)]
