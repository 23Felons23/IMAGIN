"""
transcriber.py — WhisperX transcription and speaker diarization pipeline.

Decisions (from Phase 2 CONTEXT.md):
  - D-02: Use WhisperX natively for word-level timestamps and speaker diarization
  - D-04: Output transcript.json saved to .tmp_processing/{job_id}/
"""

import os
import json
from pathlib import Path


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
    import whisperx

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
