#!/usr/bin/env python3
"""
Download XTTS-v2 models
"""
import os
from pathlib import Path
from TTS.api import TTS

def main():
    """Download XTTS-v2 model"""
    print("=" * 60)
    print("Downloading XTTS-v2 Model")
    print("=" * 60)
    print("\nThis may take 5-10 minutes depending on your internet speed...")
    print("Model size: ~1.8GB\n")

    # Set model cache directory
    models_dir = Path("/models")
    models_dir.mkdir(exist_ok=True)

    # Set TTS cache to our models directory
    os.environ['TTS_HOME'] = str(models_dir)

    try:
        # Initialize TTS with XTTS-v2 (this downloads the model)
        print("Initializing TTS with XTTS-v2...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

        print("\n✅ Successfully downloaded XTTS-v2 model!")
        print(f"📁 Model stored in: {models_dir}")
        print(f"💾 Total size: ~1.8GB")

        # Print model info
        print("\n📊 Model Information:")
        print(f"   - Languages: {len(tts.languages)} supported")
        print(f"   - Voice cloning: ✅ Enabled")
        print(f"   - Multi-lingual: ✅ Yes")

    except Exception as e:
        print(f"\n❌ Error downloading model: {e}")
        exit(1)

if __name__ == "__main__":
    main()
