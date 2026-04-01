import numpy as np
if not hasattr(np, "NaN"):
    np.NaN = np.nan
if not hasattr(np, "float_"):
    np.float_ = float

import torch
import whisperx
import os
from dotenv import load_dotenv

load_dotenv()

print(f"🐍 Python Version: 3.11.x confirmed")
print(f"🔥 CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"🎮 GPU Device: {torch.cuda.get_device_name(0)}")

ffmpeg_path = os.environ.get("FFMPEG_PATH", "ffmpeg")
print(f"🎬 FFmpeg Path: {ffmpeg_path}")
print(f"✅ FFmpeg Exists: {os.path.exists(ffmpeg_path)}")

print("\n🚀 Environment check complete. Ready for pipeline execution.")
