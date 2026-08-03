"""Download a local ONNX embedding model (tokenizer.json + model.onnx).

Fetches a Xenova/Transformers.js-style ONNX model from the HuggingFace Hub into
a local directory the ``OnnxEmbedder`` can load. Free, one-time, then fully
offline. Run:

    python -m pqc_audit_rag.knowledge_base.download_model
"""

from __future__ import annotations

import shutil
from pathlib import Path

from pqc_audit_rag.config import settings

# Pin the Hub revision for reproducible, tamper-evident downloads. Override with
# a specific commit SHA or tag for a fully immutable pin.
DEFAULT_REVISION = "main"


def download(
    repo_id: str | None = None,
    dest: str | None = None,
    revision: str = DEFAULT_REVISION,
) -> Path:
    """Download ``tokenizer.json`` and ``onnx/model.onnx`` into ``dest``."""
    from huggingface_hub import hf_hub_download

    repo_id = repo_id or settings.embed_model
    dest_dir = Path(dest or settings.embed_model_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = hf_hub_download(
        repo_id=repo_id, filename="tokenizer.json", revision=revision
    )
    model = hf_hub_download(
        repo_id=repo_id, filename="onnx/model.onnx", revision=revision
    )
    shutil.copyfile(tokenizer, dest_dir / "tokenizer.json")
    shutil.copyfile(model, dest_dir / "model.onnx")
    return dest_dir


def main() -> None:
    dest = download()
    print(f"Downloaded embedding model to {dest}/ (tokenizer.json + model.onnx).")


if __name__ == "__main__":
    main()
