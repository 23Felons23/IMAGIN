# Phase 4: Dynamic Video Rendering (Remotion) - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Consume `highlights.json` + original video files + `transcript.json` from previous phases and use Remotion (React, programmatic rendering) to produce final 9:16 vertical MP4 clips with:
- Auto camera switching based on user-provided speaker-to-camera mapping
- Word-by-word bouncy "Hormozi-style" subtitles synced to timestamps
- Rule-based emoji keyword overlays
- Output triggered automatically by FastAPI background task after highlights are ready

</domain>

<decisions>
## Implementation Decisions

### Architecture
- **D-01:** Remotion lives in a separate `remotion/` folder at the project root. Python backend triggers rendering via `subprocess` calling `npx remotion render`.

### Camera Switching
- **D-02:** Manual mapping via a `camera_config.json` the user uploads alongside the video. Format: `{"SPEAKER_00": "camera1.mp4", "SPEAKER_01": "camera2.mp4"}`. If absent, all scenes default to `camera1.mp4`.
- **D-03:** The Python bridge resolves the active speaker per word from `transcript.json` and writes a `render_config.json` that Remotion reads — this pre-computes all camera switch timestamps so Remotion doesn't need to do any logic, just read and render.

### Subtitle Style
- **D-04:** **Word-by-word pop** — each word animates in as it's spoken. Properties:
  - Bold white text, heavy black stroke (`-webkit-text-stroke` / SVG stroke)
  - Scale-up spring animation on entry (0.5 → 1.0 scale over ~6 frames)
  - Bright accent color on the currently-speaking word (e.g. #FF3366)
  - Previous words fade to white/grey to keep focus on current word

### Emoji Overlays
- **D-05:** Rule-based keyword dictionary in `emoticons.ts` — maps keywords to emojis (e.g. `{money: "💰", fire: "🔥", crazy: "🤯", love: "❤️"}`). Matched case-insensitively against each word. Emoji floats above the word for ~12 frames on match.

### Rendering Trigger
- **D-06:** FastAPI background task calls `npx remotion render` as a subprocess after `highlights_ready` status. Each highlight clip renders as a separate MP4 file. Job status updates to `rendering` → `complete`.
- **D-07:** Output files written to `.tmp_processing/{job_id}/clips/clip_01.mp4`, `clip_02.mp4`, etc.

</decisions>

<canonical_refs>
## Canonical References

- `backend/highlight_serializer.py` — Output schema: `[{start, end, score, reason, mode}]`
- `backend/transcriber.py` — Transcript schema: `[{word, start, end, speaker}]`
- `backend/main.py` — Pipeline integration point (status: highlights_ready → rendering → complete)
- `.planning/REQUIREMENTS.md` — REND-01 through REND-05
</canonical_refs>
