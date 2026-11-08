import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download


MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_PATH = Path(os.getenv("MODEL_PATH", "/models/model"))
HF_TOKEN = os.getenv("HF_TOKEN")

MARKER = MODEL_PATH.parent / ".model_cache_id"


def model_is_complete():
    has_config = (MODEL_PATH / "config.json").is_file()

    has_weights = (
        any(MODEL_PATH.rglob("*.safetensors"))
        or any(MODEL_PATH.rglob("*.bin"))
    )

    return has_config and has_weights


def main():
    MODEL_PATH.mkdir(parents=True, exist_ok=True)

    if MARKER.exists():
        cached_model = MARKER.read_text().strip()

        if cached_model != MODEL_NAME:
            raise RuntimeError(
                f"Cache contains {cached_model}, "
                f"but requested {MODEL_NAME}. "
                "Use a separate MODEL_PATH for another model."
            )

        if model_is_complete():
            print("Model already exists in PVC. Skipping download.")
            return

    print(f"Downloading model: {MODEL_NAME}")

    snapshot_download(
        repo_id=MODEL_NAME,
        local_dir=str(MODEL_PATH),
        token=HF_TOKEN or None,
    )

    if not model_is_complete():
        raise RuntimeError("Model download is incomplete.")

    temp_marker = MARKER.with_suffix(".tmp")
    temp_marker.write_text(MODEL_NAME)
    temp_marker.replace(MARKER)

    print(f"Model successfully cached at {MODEL_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Model download failed: {error}", file=sys.stderr)
        sys.exit(1)