# Summary: 02-02 Multicam Audio Extraction & Cross-Correlation Sync

- **Status**: Complete
- **Self-Check**: PASSED

## Deliverables
- `backend/audio_sync.py`

## What was built
`extract_audio()` wraps FFmpeg to produce 16kHz mono WAV from any video file. `find_audio_offset()` loads both WAVs into NumPy float64 arrays, trims to equal length, and uses `scipy.signal.fftconvolve` to detect the sample-level lag, returning precise seconds. `align_cameras()` is the high-level entry point that extracts all cameras, computes all offsets relative to master, and returns an offset map for downstream rendering.
