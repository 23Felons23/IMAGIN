# Summary: 02-03 Transcription and Speaker Diarization (WhisperX)

- **Status**: Complete
- **Self-Check**: PASSED

## Deliverables
- `backend/transcriber.py`

## What was built
`transcribe_and_diarize()` chains the full WhisperX pipeline: load model → transcribe → align for word-level timestamps → optional speaker diarization via pyannote (requires HF token). Outputs a flat list of `{word, start, end, speaker}` objects saved as `transcript.json`. Auto-detects CUDA for GPU acceleration, falls back to CPU int8. Integrated in `main.py`'s background pipeline task to trigger after audio extraction completes.
