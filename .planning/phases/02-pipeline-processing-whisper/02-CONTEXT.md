# Phase 2: Pipeline Processing (Whisper) - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary
Implement the primary API receiver (FastAPI) and the automated Python-based audio processing pipeline using WhisperX for diarization and SciPy for multicam alignment.
</domain>

<decisions>
## Implementation Decisions

### Audio Sync & Alignment
- **D-01:** Sync dynamically using audio waveform cross-correlation (`scipy.signal`). Do not assume pre-synced timecodes.

### Speaker Diarization
- **D-02:** Use WhisperX natively to achieve highly accurate speaker separation and word-level timestamps without needing a separate LLM round trip for guessations.

### Task Queue Architecture
- **D-03:** Use a prioritized lightweight architecture via FastAPI `BackgroundTasks`. We avoid Celery/Redis overhead for V1 simplicity.

### File Storage Strategy
- **D-04:** Process large media files locally in a `.tmp_processing` directory at the project root. Clean this directory programmatically after rendering to prevent disk buildup over time.
</decisions>
