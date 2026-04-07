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
    overlap_seconds: float = 60.0,
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
        overlap_seconds: Overlap between windows (default 60s to cover full clip length)
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


def deduplicate_highlights(highlights: list[dict], threshold: float = 0.85) -> list[dict]:
    """
    Remove nearly identical highlights using Non-Maximum Suppression (NMS).
    Two highlights are considered duplicates if their overlap ratio is > threshold.
    Overlapping is generally fine, but we avoid nearly identical moments.
    """
    if not highlights:
        return []

    # Sort by score descending
    sorted_hl = sorted(highlights, key=lambda x: x["score"], reverse=True)
    kept = []

    for candidate in sorted_hl:
        is_duplicate = False
        for existing in kept:
            # Calculate intersection
            inter_start = max(candidate["start"], existing["start"])
            inter_end = min(candidate["end"], existing["end"])
            
            if inter_end > inter_start:
                intersection = inter_end - inter_start
                # Ratio relative to the shorter of the two
                cand_dur = candidate["end"] - candidate["start"]
                exis_dur = existing["end"] - existing["start"]
                min_dur = min(cand_dur, exis_dur)
                
                overlap_ratio = intersection / min_dur
                if overlap_ratio > threshold:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            kept.append(candidate)

    return kept


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

def calculate_rendered_duration(
    words: list[dict],
    start: float,
    end: float,
    cuts: list[dict]
) -> float:
    """
    Dry-run the jump-cut logic to estimate the FINAL rendered duration of a clip.
    This must match the logic in build_render_config in render_bridge.py.
    """
    SILENCE_THRESHOLD = 0.4
    KEEP_SILENCE = 0.1
    
    # Filter words in range and not in AI cuts
    filtered_words = []
    for w in words:
        if w["end"] < start or w["start"] > end:
            continue
        is_filler = False
        for cut in cuts:
            if w["start"] >= cut["start"] and w["end"] <= cut["end"]:
                is_filler = True
                break
        if not is_filler:
            filtered_words.append(w)
            
    if not filtered_words:
        return 0.0

    rendered_cursor = 0.0
    current_segment_source_start = start
    
    for i in range(len(filtered_words)):
        w = filtered_words[i]
        w_start_source = w["start"]
        w_end_source = w["end"]
        
        if i == 0:
            gap_duration = w_start_source - start
        else:
            gap_duration = w_start_source - filtered_words[i-1]["end"]
            
        if gap_duration > SILENCE_THRESHOLD:
            source_end = w_start_source - gap_duration + (KEEP_SILENCE / 2.0)
            duration = source_end - current_segment_source_start
            if duration > 0:
                rendered_cursor += duration
            current_segment_source_start = w_start_source - (KEEP_SILENCE / 2.0)
            
    final_duration = end - current_segment_source_start
    if final_duration > 0:
        rendered_cursor += final_duration
        
    return rendered_cursor


MULTIMODAL_SYSTEM_PROMPT = """You are an expert podcast video editor.

Given a transcript segment with timestamps, identify the most engaging and compelling CONTIGUOUS moments. 
The transcript may be in English or French; analyze it in its original language.

Identify ALL top highlights in this segment. For each highlight, find its core and identify any filler phrases or tangents to cut.

Rules:
- CRITICAL CONTEXT: Ensure the clip includes the full SETUP for a cold viewer. If the main point refers to something mentioned 30-40 seconds earlier (a question, an object, a premise), you MUST start the clip early enough to include that context. Do not just capture the punchline.
- Highlights CAN overlap with each other if that's what makes them better. Do not worry about redundancy.
- The FINAL rendered duration (after you remove filler and silence) SHOULD be around 30-40 seconds.
- You can go slightly longer (up to 45 seconds) if the content is highly engaging and cannot be cut further without losing the message or context.
- You can pick a longer original segment (up to 75s) if you suggest significant cuts to bring the final version closer to 30-45s.
- The moments must be fully contained within the provided transcript.
- Pick naturally flowing segments — complete thoughts or story arcs.
- Output ONLY valid JSON with this exact structure:
  {"highlights": [{"start": <float seconds>, "end": <float seconds>, "score": <float 0-1>, "reason": <string>, "suggested_cuts": [{"start": <float>, "end": <float>, "reason": <string>}]}]}

CRITICAL: You MUST return AT LEAST 2 highlights per segment. Even if the segment is boring or the topic is barely mentioned, find the "least bad" parts and give them a low score (e.g., 0.1). Never return an empty list or fewer than 2 items.
CRITICAL: Use the ABSOLUTE timestamps from the transcript in SECONDS (e.g. if the window is [00:05:00], timestamps should be > 300.0, NOT 0.0 to 30.0). Output ONLY the JSON.
"""


def score_chunk_with_llm(chunk: dict, llm_complete) -> list[dict]:
    """
    Ask the LLM to identify ALL best contiguous highlights within a chunk,
    including filler segments to cut. Returns a list of validated highlights.
    """
    transcript_text = _format_chunk_as_text(chunk)
    user_prompt = (
        f"Transcript window [{_fmt_seconds(chunk['chunk_start'])} → {_fmt_seconds(chunk['chunk_end'])}]:\n\n"
        f"{transcript_text}\n\n"
        "Identify ALL great highlights (target 30s, max 40s rendered duration) in this window."
    )

    raw = llm_complete(MULTIMODAL_SYSTEM_PROMPT, user_prompt)
    print(f"      🤖 LLM RAW OUTPUT:\n{raw}\n")
    result = _parse_llm_json(raw)
    if not result or "highlights" not in result:
        return []

    validated_highlights = []
    chunk_words = chunk["words"]
    
    for hl in result.get("highlights", []):
        start = float(hl.get("start", 0))
        end = float(hl.get("end", 0))
        
        if start >= end:
            continue

        # Clamping
        clamped_start = max(start, chunk["chunk_start"])
        clamped_end = min(end, chunk["chunk_end"])
        
        if clamped_start >= clamped_end:
            print(f"      ❌ Rejected: clamped start ({clamped_start}) >= clamped end ({clamped_end}) - LLM likely hallucinated timestamps.")
            continue

        # Handle suggested cuts
        suggested_cuts = hl.get("suggested_cuts", [])
        valid_cuts = []
        for cut in suggested_cuts:
            c_start = float(cut.get("start", 0))
            c_end = float(cut.get("end", 0))
            if c_start < c_end and c_start >= clamped_start and c_end <= clamped_end:
                valid_cuts.append({
                    "start": c_start,
                    "end": c_end,
                    "reason": str(cut.get("reason", "filler"))
                })

        # Calculate FINAL Rendered Duration
        rendered_dur = calculate_rendered_duration(chunk_words, clamped_start, clamped_end, valid_cuts)
        
        if rendered_dur > 45.2:
            print(f"      ❌ Rejected: rendered duration too long ({rendered_dur:.1f}s > 45s)")
            continue
        if rendered_dur < 5.0:
            print(f"      ❌ Rejected: rendered duration too short ({rendered_dur:.1f}s < 5s)")
            continue

        validated_highlights.append({
            "start": clamped_start,
            "end": clamped_end,
            "score": float(hl.get("score", 0)),
            "reason": str(hl.get("reason", "")),
            "suggested_cuts": valid_cuts,
            "rendered_duration": round(rendered_dur, 2)
        })

    return validated_highlights


def extract_highlights_multimodal(
    transcript_path: str,
    audio_path: str,
    top_n: int = 3,
    window_seconds: float | None = None,
) -> list[dict]:
    """
    Extract top N highlights using combined audio energy + LLM engagement scoring.
    """
    from llm_client import get_llm_client

    window_secs = window_seconds or float(os.environ.get("HIGHLIGHT_WINDOW_SECONDS", 300))
    llm_complete = get_llm_client()

    with open(transcript_path) as f:
        words = json.load(f)

    candidates = []
    chunks = list(chunk_transcript(words, window_seconds=window_secs))
    total_chunks = len(chunks)
    
    print(f"  🔍 Analyzing {total_chunks} windows for highlights...")
    
    for i, chunk in enumerate(chunks, start=1):
        print(f"    - Window {i}/{total_chunks} [{_fmt_seconds(chunk['chunk_start'])} → {_fmt_seconds(chunk['chunk_end'])}]")
        audio_energy = score_audio_energy(audio_path, chunk["chunk_start"], chunk["chunk_end"])
        
        llm_highlights = score_chunk_with_llm(chunk, llm_complete)
        for hl in llm_highlights:
            combined_score = 0.2 * audio_energy + 0.8 * hl["score"]
            print(f"      ✅ Highlight ({hl['rendered_duration']}s) | Score: {combined_score:.4f} (LLM: {hl['score']}, Audio: {audio_energy:.2f}) | Reason: {hl['reason'][:60]}...")
            candidates.append({
                **hl,
                "llm_score": hl["score"],
                "audio_score": round(audio_energy, 4),
                "score": round(combined_score, 4),
                "mode": "multimodal",
            })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return deduplicate_highlights(candidates)[:top_n]


TOPIC_SYSTEM_PROMPT = """You are an expert podcast video editor.

Given a transcript segment with timestamps and a target topic, find ALL the most relevant CONTIGUOUS moments that discuss that topic.

Within each moment, identify any filler phrases or tangents to cut.

Rules:
- CRITICAL CONTEXT: Ensure the clip includes the full SETUP for a cold viewer. If the main point refers to something mentioned 30-40 seconds earlier (a question, an object, a premise), you MUST start the clip early enough to include that context. Do not just capture the punchline.
- Highlights CAN overlap with each other if that's what makes them better. Do not worry about redundancy.
- The FINAL rendered duration (after you remove filler and silence) SHOULD be around 30-40 seconds.
- You can go slightly longer (up to 45 seconds) if the content is highly engaging and cannot be cut further.
- You can pick a longer original segment (up to 75s) if you suggest cuts to bring it under 30-45s.
- The moments must be fully contained within the provided transcript.
- Output ONLY valid JSON with this exact structure:
  {"highlights": [{"start": <float seconds>, "end": <float seconds>, "score": <float 0-1>, "reason": <string>, "suggested_cuts": [{"start": <float>, "end": <float>, "reason": <string>}]}]}

CRITICAL: You MUST return AT LEAST 2 highlights per segment. Even if the segment is boring or the topic is barely mentioned, find the "least bad" parts and give them a low score (e.g., 0.1). Never return an empty list or fewer than 2 items.
CRITICAL: Use the ABSOLUTE timestamps from the transcript in SECONDS (e.g. if the window is [00:05:00], timestamps should be > 300.0, NOT 0.0 to 30.0). Output ONLY the JSON.
"""


def extract_highlights_topic(
    transcript_path: str,
    topic_prompt: str,
    top_n: int = 3,
    window_seconds: float | None = None,
) -> list[dict]:
    """
    Extract top N highlights most relevant to a user-provided topic prompt.
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
            "Identify ALL relevant highlights (target 30s, max 40s rendered duration) for the given topic."
        )

        raw = llm_complete(system_prompt, user_prompt)
        result = _parse_llm_json(raw)
        if not result or "highlights" not in result:
            continue

        chunk_words = chunk["words"]
        for hl in result.get("highlights", []):
            score = float(hl.get("score", 0))
            # Keep even low scores to ensure we get some clips

            start = float(hl.get("start", 0))
            end = float(hl.get("end", 0))
            
            if start >= end:
                continue

            # Clamping
            clamped_start = max(start, chunk["chunk_start"])
            clamped_end = min(end, chunk["chunk_end"])
            
            if clamped_start >= clamped_end:
                print(f"      ❌ Rejected topic highlight: clamped start ({clamped_start}) >= clamped end ({clamped_end})")
                continue

            # Handle suggested cuts
            suggested_cuts = hl.get("suggested_cuts", [])
            valid_cuts = []
            for cut in suggested_cuts:
                c_start = float(cut.get("start", 0))
                c_end = float(cut.get("end", 0))
                if c_start < c_end and c_start >= clamped_start and c_end <= clamped_end:
                    valid_cuts.append({
                        "start": c_start,
                        "end": c_end,
                        "reason": str(cut.get("reason", "filler"))
                    })

            # Calculate FINAL Rendered Duration
            rendered_dur = calculate_rendered_duration(chunk_words, clamped_start, clamped_end, valid_cuts)
            
            if rendered_dur > 45.2:
                print(f"      ❌ Rejected topic highlight: rendered duration too long ({rendered_dur:.1f}s > 45s)")
                continue
            if rendered_dur < 5.0:
                print(f"      ❌ Rejected topic highlight: rendered duration too short ({rendered_dur:.1f}s < 5s)")
                continue

            candidates.append({
                "start": clamped_start,
                "end": clamped_end,
                "score": round(score, 4),
                "reason": str(hl.get("reason", "")),
                "mode": "topic",
                "topic": topic_prompt,
                "suggested_cuts": valid_cuts,
                "rendered_duration": round(rendered_dur, 2)
            })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return deduplicate_highlights(candidates)[:top_n]
