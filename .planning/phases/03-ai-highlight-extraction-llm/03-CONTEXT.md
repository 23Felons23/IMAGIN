# Phase 3: AI Highlight Extraction (LLM) - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Take `transcript.json` (word-level `{word, start, end, speaker}` array from Phase 2) and use an LLM to identify the most compelling contiguous clips. Output structured JSON for Remotion + a human-readable markdown summary.

</domain>

<decisions>
## Implementation Decisions

### LLM Provider
- **D-01:** Start with **OpenAI GPT-4o** (`LLM_PROVIDER=openai`). Architect with a provider abstraction layer so switching to Anthropic or local Ollama requires only changing the env var — no code changes.

### Multimodal Energy Detection
- **D-02:** Use **librosa RMS amplitude analysis** to score audio energy per time window. Combine this signal with LLM engagement scoring of the transcript text to rank windows. High amplitude + high LLM engagement score = highlight candidate.

### Output Format
- **D-03:** Output **both**:
  - `highlights.json` — machine-readable array `[{start, end, score, reason}]` consumed directly by Remotion renderer
  - `highlights.md` — human-readable summary with speaker breakdown and reasoning, for review before rendering

### Clip Duration & Timeline Contiguity
- **D-04:** Clip duration is **soft** — LLM picks natural start/end points at sentence/topic boundaries, no hard clamp.
- **D-05:** **Timeline contiguity is strictly enforced** via sliding window chunking. The transcript is sliced into overlapping windows of ~3–5 minutes (configurable via `HIGHLIGHT_WINDOW_SECONDS`, default 300s). Each LLM call operates only within one window and returns a single `{start, end}` pair from that window. This physically prevents the LLM from combining moments separated by an hour into one fake clip.
- **D-06:** Windows overlap by 30s to avoid cutting a highlight at a window boundary.

</decisions>

<canonical_refs>
## Canonical References

- `backend/transcriber.py` — Output schema: `[{word, start, end, speaker}]`
- `backend/main.py` — BackgroundTasks integration point for the highlight extractor
- `.planning/REQUIREMENTS.md` — AI-01 (multimodal), AI-02 (topic-driven)
- `backend/.env.example` — LLM_PROVIDER, OPENAI_API_KEY, HIGHLIGHT_WINDOW_SECONDS
</canonical_refs>
