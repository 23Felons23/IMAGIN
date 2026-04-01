"""
highlight_serializer.py — Dual output serialization for highlight results.

Saves:
  - highlights.json  → machine-readable for Remotion renderer
  - highlights.md    → human-readable for review before rendering
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def _fmt_seconds(s: float) -> str:
    """Format seconds as HH:MM:SS."""
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def save_highlights_json(
    highlights: list[dict],
    output_path: str,
) -> None:
    """
    Save highlights as machine-readable JSON for the Remotion renderer.

    Args:
        highlights: List of {start, end, score, reason, mode, ...} dicts
        output_path: Destination file path (e.g. .tmp_processing/{job_id}/highlights.json)
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(highlights, f, indent=2)


def save_highlights_markdown(
    highlights: list[dict],
    output_path: str,
    mode: str,
    topic_prompt: str | None = None,
) -> None:
    """
    Save highlights as a human-readable Markdown report for review.

    Args:
        highlights: List of highlight dicts
        output_path: Destination .md file path
        mode: "multimodal" or "topic"
        topic_prompt: The user's topic string (only when mode="topic")
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if mode == "topic" and topic_prompt:
        mode_label = f'topic: "{topic_prompt}"'
    else:
        mode_label = "multimodal (energy + engagement)"

    lines = [
        "# Highlight Report",
        "",
        f"**Mode:** {mode_label}  ",
        f"**Generated:** {now}  ",
        f"**Clips found:** {len(highlights)}",
        "",
        "---",
        "",
    ]

    for i, clip in enumerate(highlights, start=1):
        start_fmt = _fmt_seconds(clip["start"])
        end_fmt = _fmt_seconds(clip["end"])
        duration = clip["end"] - clip["start"]
        score_pct = int(clip["score"] * 100)

        lines += [
            f"## Clip {i} — {start_fmt} → {end_fmt}",
            "",
            f"**Duration:** {duration:.1f}s  ",
            f"**Score:** {score_pct}%  ",
            "",
            f"> {clip.get('reason', 'No reason provided.')}",
            "",
            "---",
            "",
        ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
