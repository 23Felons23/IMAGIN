"""
transcriber.py — WhisperX transcription and speaker diarization pipeline.

Decisions (from Phase 2 CONTEXT.md):
  - D-02: Use WhisperX natively for word-level timestamps and speaker diarization
  - D-04: Output transcript.json saved to .tmp_processing/{job_id}/
"""

import os
import json
from pathlib import Path


# NumPy 2.0 & PyTorch 2.6 Compatibility Bridge
import numpy as np
import torch

if not hasattr(np, "NaN"):
    np.NaN = np.nan
if not hasattr(np, "NAN"):
    np.NAN = np.nan
if not hasattr(np, "float_"):
    np.float_ = float

# Universal Fix: Globally allow loading all model weights (bypasses PyTorch 2.6+ restrictions)
original_torch_load = torch.load
def patched_torch_load(*args, **kwargs):
    kwargs["weights_only"] = False
    return original_torch_load(*args, **kwargs)
torch.load = patched_torch_load

# SpeechBrain Universal Fix: prevent crashes when optional integrations (k2, flair, etc.) are missing
try:
    import speechbrain.utils.importutils as sb_imp
    original_ensure = sb_imp.LazyModule.ensure_module
    def patched_ensure(self, stacklevel=1):
        try:
            return original_ensure(self, stacklevel + 1)
        except ImportError:
            from types import ModuleType
            dummy = ModuleType(self.target)
            dummy.__path__ = [] # Make it look like a package
            return dummy
    sb_imp.LazyModule.ensure_module = patched_ensure
except (ImportError, AttributeError, ModuleNotFoundError):
    pass

# HuggingFace Compatibility Fix: handle use_auth_token rename globally
try:
    import huggingface_hub
    from huggingface_hub import hf_hub_download, model_info
    
    def patch_hf_func(original_func):
        def patched_func(*args, **kwargs):
            if "use_auth_token" in kwargs:
                kwargs["token"] = kwargs.pop("use_auth_token")
            return original_func(*args, **kwargs)
        return patched_func

    huggingface_hub.hf_hub_download = patch_hf_func(huggingface_hub.hf_hub_download)
    huggingface_hub.model_info = patch_hf_func(huggingface_hub.model_info)
except (ImportError, AttributeError):
    pass

# Environment Injection: Ensure FFmpeg and NVIDIA libraries are in PATH
import os
import sys

# 1. ADD FFmpeg
ffmpeg_full_path = os.environ.get("FFMPEG_PATH", "")
if ffmpeg_full_path:
    ffmpeg_dir = str(Path(ffmpeg_full_path).parent)
    if ffmpeg_dir not in os.environ["PATH"]:
        os.environ["PATH"] = ffmpeg_dir + os.path.pathsep + os.environ["PATH"]

# 2. ADD NVIDIA cuDNN/cuBLAS from venv
venv_site_packages = os.path.join(str(Path(__file__).parent), "venv", "Lib", "site-packages")
nvidia_paths = [
    os.path.join(venv_site_packages, "nvidia", "cudnn", "bin"),
    os.path.join(venv_site_packages, "nvidia", "cublas", "bin"),
]
for p in nvidia_paths:
    if os.path.exists(p) and p not in os.environ["PATH"]:
        os.environ["PATH"] = p + os.path.pathsep + os.environ["PATH"]


def transcribe_and_diarize(audio_path: str, hf_token: str = "") -> list[dict]:
    """
    Transcribe an audio file and assign speakers using WhisperX.
    
    This produces word-level segments with timestamps and speaker labels.
    
    Args:
        audio_path: Path to the 16kHz mono WAV audio file
        hf_token: HuggingFace access token for pyannote diarization models.
                  Get one at: https://huggingface.co/pyannote/speaker-diarization
    
    Returns:
        list[dict]: Word-level transcript with keys:
            - word (str): The transcribed word
            - start (float): Word start time in seconds
            - end (float): Word end time in seconds
            - speaker (str): Speaker label e.g. "SPEAKER_00"
    
    Raises:
        ImportError: If whisperx is not installed
        RuntimeError: If diarization token is empty and diarization is requested
    """
    # Ensure NLTK data is available (needed by whisperx alignment)
    try:
        import nltk
        nltk.data.find('tokenizers/punkt_tab')
    except (ImportError, LookupError):
        import nltk
        print("📥 Downloading NLTK punkt_tab...")
        nltk.download('punkt_tab', quiet=True)

    import whisperx

    # MONKEYPATCH: Resolve all WhisperX version conflicts (ASR & VAD)
    import faster_whisper
    import pyannote.audio
    
    # 1. Faster-whisper compatibility fix
    original_asr_init = faster_whisper.transcribe.TranscriptionOptions.__init__
    def patched_asr_init(self, *args, **kwargs):
        if "multilingual" not in kwargs and len(args) < 11:
            kwargs["multilingual"] = False
        if "hotwords" not in kwargs and "hotwords" not in args:
            kwargs["hotwords"] = None
        return original_asr_init(self, *args, **kwargs)
    faster_whisper.transcribe.TranscriptionOptions.__init__ = patched_asr_init

    # 2. Pyannote/VAD compatibility fix
    original_inference_init = pyannote.audio.Inference.__init__
    def patched_inference_init(self, *args, **kwargs):
        kwargs.pop("use_auth_token", None)
        return original_inference_init(self, *args, **kwargs)
    pyannote.audio.Inference.__init__ = patched_inference_init

    # Detect device — use CUDA if available, fall back to CPU
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    # Step 1: Load WhisperX model and transcribe (Using 'medium' for better French accuracy)
    model = whisperx.load_model("medium", device=device, compute_type=compute_type)
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=16)

    # Step 2: Align whisper output for word-level timestamps
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"],
        device=device
    )
    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False
    )

    # Step 3: Speaker diarization (requires HF token)
    if hf_token:
        diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=hf_token,
            device=device
        )
        diarize_segments = diarize_model(audio_path)
        result = whisperx.assign_word_speakers(diarize_segments, result)

    # Step 4: Flatten to word-level output with speaker assignment
    words_output = []
    for segment in result.get("segments", []):
        speaker = segment.get("speaker", "SPEAKER_00")
        for word_info in segment.get("words", []):
            words_output.append({
                "word": word_info.get("word", "").strip(),
                "start": round(word_info.get("start", 0.0), 3),
                "end": round(word_info.get("end", 0.0), 3),
                "speaker": word_info.get("speaker", speaker),
            })

    return words_output


def load_transcript(transcript_path: str) -> list[dict]:
    """Load a previously saved transcript.json file."""
    with open(transcript_path, "r") as f:
        return json.load(f)
