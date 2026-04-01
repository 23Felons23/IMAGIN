"""
highlight_extractor.py — AI-powered highlight detection using sliding time windows.

Two modes:
  - Multimodal: librosa audio RMS energy + LLM engagement scoring
  - Topic-driven: LLM relevance scoring against a user-provided text prompt

Timeline contiguity is guaranteed by architecture: the transcript is sliced
into overlapping windows (default 300s / 5 min with 30s overlap). Each LLM
call operates only within one window, so it physically cannot stitch together
moments from different parts of the video.
"""

import json
import os
import re
from pathlib import Path
from typing import Generator


# ---------------------------------------------------------------------------
# Sliding window chunker
# ---------------------------------------------------------------------------

def chunk_transcript(
    words: list[dict],
    window_seconds: float = 300.0,
    overlap_seconds: float = 30.0,
) -> Generator[dict, None, None]:
    """
    Yield overlapping windows of the transcript word list.

    Each yielded chunk is:
        {
            "words": [...],        # subset of the full word list
            "chunk_start": float,  # earliest word start time in this chunk
            "chunk_end": float,    # latest word end time in this chunk
        }

    Args:
        words: Flat list of {word, start, end, speaker} dicts
        window_seconds: Size of each window in seconds (default 300 = 5 min)
        overlap_seconds: Overlap between consecutive windows (default 30s)
    """
    if not words:
        return

    step = window_seconds - overlap_seconds
    video_start = words[0]["start"]
    video_end = words[-1]["end"]

    window_left = video_start
    while window_left < video_end:
        window_right = window_left + window_seconds
        chunk_words = [
            w for w in words
            if w["start"] >= window_left and w["end"] <= window_right
        ]
        if chunk_words:
            yield {
                "words": chunk_words,
                "chunk_start": chunk_words[0]["start"],
                "chunk_end": chunk_words[-1]["end"],
            }
        window_left += step


def _format_chunk_as_text(chunk: dict) -> str:
    """Format a word chunk into readable transcript text with timestamps."""
    lines = []
    current_speaker = None
    current_line = []
    current_start = None

    for w in chunk["words"]:
        speaker = w.get("speaker", "SPEAKER_00")
        if speaker != current_speaker:
            if current_line:
                ts = f"[{_fmt_seconds(current_start)}]"
                lines.append(f"{current_speaker} {ts}: {' '.join(current_line)}")
            current_speaker = speaker
            current_line = [w["word"]]
            current_start = w["start"]
        else:
            current_line.append(w["word"])

    if current_line:
        ts = f"[{_fmt_seconds(current_start)}]"
        lines.append(f"{current_speaker} {ts}: {' '.join(current_line)}")

    return "\n".join(lines)


def _fmt_seconds(s: float) -> str:
    """Format seconds as HH:MM:SS."""
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def _parse_llm_json(raw: str) -> dict | None:
    """Parse JSON from LLM response, tolerating markdown fences."""
    # Strip ```json ... ``` fences if present
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Audio energy scoring
# ---------------------------------------------------------------------------

def score_audio_energy(audio_path: str, chunk_start: float, chunk_end: float) -> float:
    """
    Compute normalized RMS energy for a time segment of an audio file.

    Returns:
        float: 0.0–1.0 (normalized by the max RMS of the full file)
    """
    import librosa
    import numpy as np

    y, sr = librosa.load(audio_path, sr=None, offset=chunk_start, duration=chunk_end - chunk_start)
    if len(y) == 0:
        return 0.0

    chunk_rms = float(np.sqrt(np.mean(y ** 2)))

    # Load full file for normalization reference
    y_full, _ = librosa.load(audio_path, sr=None)
    frame_rms = librosa.feature.rms(y=y_full)[0]
    max_rms = float(frame_rms.max()) if frame_rms.max() > 0 else 1.0

    return min(chunk_rms / max_rms, 1.0)


# ---------------------------------------------------------------------------
# Multimodal highlight extraction (energy + LLM)
# ---------------------------------------------------------------------------

MULTIMODAL_SYSTEM_PROMPT = """You are an expert podcast video editor.

Given a transcript segment with timestamps, identify the single most engaging and compelling CONTIGUOUS moment. 
The transcript may be in English or French; analyze it in its original language.

Rules:
- The moment must be fully contained within the provided transcript (do not invent timestamps outside it)
- Pick a naturally flowing segment — a complete thought, story arc, or debate
- Output ONLY valid JSON with these exact keys:
  {"start": <float seconds>, "end": <float seconds>, "score": <float 0-1>, "reason": <string>}

Score rubric:
  0.9–1.0: Extraordinary insight, emotional peak, or viral-worthy moment
  0.7–0.8: Very engaging, clear value, good pacing
  0.5–0.6: Interesting but not exceptional
  Below 0.5: Skip this segment"""


def score_chunk_with_llm(chunk: dict, llm_complete) -> dict | None:
    """
    Ask the LLM to identify the best contiguous highlight within a chunk.

    Returns parsed dict {start, end, score, reason} or None on failure.
    """
    transcript_text = _format_chunk_as_text(chunk)
    user_prompt = (
        f"Transcript window [{_fmt_seconds(chunk['chunk_start'])} → {_fmt_seconds(chunk['chunk_end'])}]:\n\n"
        f"{transcript_text}\n\n"
        "Find the best highlight moment in this window."
    )

    raw = llm_complete(MULTIMODAL_SYSTEM_PROMPT, user_prompt)
    result = _parse_llm_json(raw)
    if not result:
        return None

    # Validate timestamps are within chunk bounds
    start = result.get("start", 0)
    end = result.get("end", 0)
    if start < chunk["chunk_start"] or end > chunk["chunk_end"] or start >= end:
        return None

    return {
        "start": float(start),
        "end": float(end),
        "score": float(result.get("score", 0)),
        "reason": str(result.get("reason", "")),
    }


def extract_highlights_multimodal(
    transcript_path: str,
    audio_path: str,
    top_n: int = 3,
    window_seconds: float | None = None,
) -> list[dict]:
    """
    Extract top N highlights using combined audio energy + LLM engagement scoring.

    Args:
        transcript_path: Path to transcript.json
        audio_path: Path to the aligned master WAV file
        top_n: Number of highlights to return
        window_seconds: Sliding window size in seconds (default from env or 300)

    Returns:
        list[dict]: Top N highlights sorted by combined score descending.
                    Each dict: {start, end, score, reason, mode}
    """
    from llm_client import get_llm_client

    window_secs = window_seconds or float(os.environ.get("HIGHLIGHT_WINDOW_SECONDS", 300))
    llm_complete = get_llm_client()

    with open(transcript_path) as f:
        words = json.load(f)

    candidates = []
    for chunk in chunk_transcript(words, window_seconds=window_secs):
        audio_energy = score_audio_energy(audio_path, chunk["chunk_start"], chunk["chunk_end"])
        llm_result = score_chunk_with_llm(chunk, llm_complete)
        if not llm_result:
            continue

        combined_score = 0.4 * audio_energy + 0.6 * llm_result["score"]
        candidates.append({
            "start": llm_result["start"],
            "end": llm_result["end"],
            "score": round(combined_score, 4),
            "reason": llm_result["reason"],
            "mode": "multimodal",
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_n]


# ---------------------------------------------------------------------------
# Topic-driven highlight extraction
# ---------------------------------------------------------------------------

TOPIC_SYSTEM_PROMPT = """You are an expert podcast video editor.

Given a transcript segment with timestamps and a target topic, find the most relevant CONTIGUOUS moment that discusses that topic.
The transcript and topic may be in English or French; analyze them accordingly.

Rules:
- The moment must be fully contained within the provided transcript
- If the topic is not meaningfully discussed in this segment, return score: 0
- Output ONLY valid JSON with these exact keys:
  {"start": <float seconds>, "end": <float seconds>, "score": <float 0-1>, "reason": <string>}

Score rubric:
  0.9–1.0: Topic is the primary focus, discussed with depth
  0.7–0.8: Topic clearly discussed, good content
  0.5–0.6: Topic mentioned but not deeply explored
  0.0: Topic not present in this segment"""


def extract_highlights_topic(
    transcript_path: str,
    topic_prompt: str,
    top_n: int = 3,
    window_seconds: float | None = None,
) -> list[dict]:
    """
    Extract top N highlights most relevant to a user-provided topic prompt.

    Args:
        transcript_path: Path to transcript.json
        topic_prompt: User's search topic (e.g. "artificial intelligence")
        top_n: Number of highlights to return
        window_seconds: Sliding window size in seconds (default from env or 300)

    Returns:
        list[dict]: Top N highlights sorted by relevance score descending.
                    Each dict: {start, end, score, reason, mode, topic}
    """
    from llm_client import get_llm_client

    window_secs = window_seconds or float(os.environ.get("HIGHLIGHT_WINDOW_SECONDS", 300))
    llm_complete = get_llm_client()

    with open(transcript_path) as f:
        words = json.load(f)

    system_prompt = TOPIC_SYSTEM_PROMPT
    candidates = []

    for chunk in chunk_transcript(words, window_seconds=window_secs):
        transcript_text = _format_chunk_as_text(chunk)
        user_prompt = (
            f'Topic to find: "{topic_prompt}"\n\n'
            f"Transcript window [{_fmt_seconds(chunk['chunk_start'])} → {_fmt_seconds(chunk['chunk_end'])}]:\n\n"
            f"{transcript_text}\n\n"
            "Find the most relevant moment for the given topic."
        )

        raw = llm_complete(system_prompt, user_prompt)
        result = _parse_llm_json(raw)
        if not result:
            continue

        score = float(result.get("score", 0))
        if score == 0:
            continue  # Topic not in this window

        start = result.get("start", 0)
        end = result.get("end", 0)
        if start < chunk["chunk_start"] or end > chunk["chunk_end"] or start >= end:
            continue

        candidates.append({
            "start": float(start),
            "end": float(end),
            "score": round(score, 4),
            "reason": str(result.get("reason", "")),
            "mode": "topic",
            "topic": topic_prompt,
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_n]
