# Summary: 03-02 Topic-Driven Extractor & Output Serialization

- **Status**: Complete
- **Self-Check**: PASSED

## Deliverables
- `backend/highlight_extractor.py` (topic section)
- `backend/highlight_serializer.py`
- `backend/main.py` (updated)

## What was built
`extract_highlights_topic()` queries the LLM per sliding window asking it to score relevance to the user's topic string, skips score=0 windows (topic absent), validates timestamp bounds, returns sorted top N clips. `highlight_serializer.py` provides `save_highlights_json()` (machine-readable `{start, end, score, reason, mode}` array for Remotion) and `save_highlights_markdown()` (human-readable HH:MM:SS formatted clip report with scores and reasons). `main.py` upload endpoint updated to accept `mode` and `topic` query params, pipeline now transitions through `extracting_highlights` → `highlights_ready` status, writing both output files to `.tmp_processing/{job_id}/`.
