#!/usr/bin/env python3
"""
Download Piper TTS voice models
"""
import os
import urllib.request
from pathlib import Path

# Model URLs - using en_US-lessac-medium (high quality, good for sustainability content)
MODEL_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

MODELS = {
    "en_US-lessac-medium": {
        "onnx": f"{MODEL_BASE_URL}/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "json": f"{MODEL_BASE_URL}/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
    },
    "en_US-amy-medium": {
        "onnx": f"{MODEL_BASE_URL}/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "json": f"{MODEL_BASE_URL}/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
    },
}

def download_file(url: str, dest_path: Path):
    """Download file with progress"""
    print(f"Downloading {url} -> {dest_path}")

    def reporthook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        print(f"\rProgress: {percent}%", end='', flush=True)

    urllib.request.urlretrieve(url, dest_path, reporthook)
    print()  # New line after progress

def main():
    """Download default voice models"""
    models_dir = Path("/models")
    models_dir.mkdir(exist_ok=True)

    # Get model from environment or use default
    default_model = os.getenv("PIPER_VOICE", "en_US-lessac-medium")

    print(f"Downloading default voice model: {default_model}")

    if default_model in MODELS:
        model_info = MODELS[default_model]

        # Download .onnx file
        onnx_path = models_dir / f"{default_model}.onnx"
        if not onnx_path.exists():
            download_file(model_info["onnx"], onnx_path)
        else:
            print(f"Model already exists: {onnx_path}")

        # Download .json config file
        json_path = models_dir / f"{default_model}.onnx.json"
        if not json_path.exists():
            download_file(model_info["json"], json_path)
        else:
            print(f"Config already exists: {json_path}")

        print(f"\n✅ Successfully downloaded {default_model}")
    else:
        print(f"❌ Unknown model: {default_model}")
        print(f"Available models: {', '.join(MODELS.keys())}")
        exit(1)

if __name__ == "__main__":
    main()
