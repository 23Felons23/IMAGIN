"""
audio_sync.py — FFmpeg audio extraction and SciPy cross-correlation multicam alignment.

Decisions (from Phase 2 CONTEXT.md):
  - D-01: Sync dynamically via waveform cross-correlation (scipy.signal)
  - D-04: Files stored under .tmp_processing/{job_id}/
"""

import subprocess
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal


def extract_audio(video_path: str, output_wav_path: str) -> None:
    """
    Extract monophonic 16kHz WAV audio from a video file via FFmpeg.
    
    Args:
        video_path: Path to the input video file (e.g. camera1.mp4)
        output_wav_path: Destination path for the output WAV file
    
    Raises:
        RuntimeError: If FFmpeg fails to extract audio
    """
    import os
    ffmpeg_exe = os.environ.get("FFMPEG_PATH", "ffmpeg")
    print(f"      DEBUG: Attempting audio extraction with: {ffmpeg_exe}")
    print(f"      DEBUG: Target file exists? {os.path.exists(ffmpeg_exe)}")

    cmd = [
        ffmpeg_exe,
        "-y",                   # Overwrite output without prompting
        "-i", video_path,
        "-ac", "1",             # Mono channel (required for stable cross-corr)
        "-ar", "16000",         # 16kHz sample rate (Whisper optimal)
        "-vn",                   # No video in output
        output_wav_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg audio extraction failed for {video_path}:\n{result.stderr}"
        )


def find_audio_offset(master_wav_path: str, secondary_wav_path: str) -> float:
    """
    Compute the time offset (in seconds) of secondary audio relative to master
    using FFT-based cross-correlation.

    A POSITIVE return value means secondary starts AFTER master.
    A NEGATIVE return value means secondary starts BEFORE master.

    Args:
        master_wav_path: Path to the reference (primary camera) WAV
        secondary_wav_path: Path to the secondary camera WAV to align

    Returns:
        float: Offset in seconds to apply to secondary stream
    """
    master_rate, master_data = wav.read(master_wav_path)
    secondary_rate, secondary_data = wav.read(secondary_wav_path)

    # Ensure both are float for numerical precision
    master_data = master_data.astype(np.float64)
    secondary_data = secondary_data.astype(np.float64)

    # Trim to same length to prevent out-of-bounds correlation
    min_len = min(len(master_data), len(secondary_data))
    master_data = master_data[:min_len]
    secondary_data = secondary_data[:min_len]

    # Cross-correlate: find delay that maximizes overlap
    # Using fftconvolve on reversed secondary against forward master
    correlation = signal.fftconvolve(master_data, secondary_data[::-1], mode="full")
    lag_samples = np.argmax(np.abs(correlation)) - (min_len - 1)

    offset_seconds = lag_samples / master_rate
    return float(offset_seconds)


def align_cameras(job_dir: str, camera_files: list[str]) -> dict:
    """
    Extract audio from all camera files and compute alignment offsets
    relative to the first (master) camera.

    Args:
        job_dir: The job's `.tmp_processing/{job_id}/` directory
        camera_files: List of video file paths (first is treated as master)

    Returns:
        dict: Mapping of camera filename → offset in seconds (master = 0.0)
    """
    job_path = Path(job_dir)
    offsets = {}

    # Extract all audio tracks
    wav_paths = {}
    for cam_file in camera_files:
        cam_path = Path(cam_file)
        wav_out = str(job_path / f"{cam_path.stem}.wav")
        extract_audio(cam_file, wav_out)
        wav_paths[cam_path.name] = wav_out

    # First camera is master — offset = 0
    camera_names = list(wav_paths.keys())
    master_name = camera_names[0]
    master_wav = wav_paths[master_name]
    offsets[master_name] = 0.0

    # Compute offsets for each secondary camera
    for cam_name in camera_names[1:]:
        offset = find_audio_offset(master_wav, wav_paths[cam_name])
        offsets[cam_name] = offset

    return offsets
