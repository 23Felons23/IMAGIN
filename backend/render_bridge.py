"""
render_bridge.py — Translates pipeline outputs into Remotion-ready render configs
and triggers npx remotion render as a subprocess per highlight clip.

Decision (D-02): Manual camera-speaker mapping via camera_config.json
Decision (D-06): FastAPI background task triggers render after highlights_ready
Decision (D-07): Output to .tmp_processing/{job_id}/clips/clip_01.mp4, etc.
"""

import json
import os
import subprocess
from pathlib import Path


def build_render_config(
    highlight: dict,
    transcript_words: list,
    video_files: dict,
) -> dict:
    """
    Build a renderConfig JSON object for a single highlight clip with Smart Silence Removal
    and AI Content Pruning.

    This identifies gaps between words and semantic filler segments, shortening them
    to create high-energy jump cuts.
    """
    clip_start = highlight["start"]
    clip_end = highlight["end"]
    suggested_cuts = highlight.get("suggested_cuts", [])

    # Configuration for Jump Cuts
    SILENCE_THRESHOLD = 0.4  # Gaps > 0.4s are considered "excessive"
    KEEP_SILENCE = 0.1       # Shorten long gaps/cuts to exactly 0.1s

    # 1. Pre-process: Filter out words that fall within AI-suggested cuts
    # (or words that overlap significantly)
    filtered_words = []
    for w in transcript_words:
        if w["end"] < clip_start or w["start"] > clip_end:
            continue
            
        is_filler = False
        for cut in suggested_cuts:
            # If word is inside a cut range, mark as filler
            if w["start"] >= cut["start"] and w["end"] <= cut["end"]:
                is_filler = True
                break
        
        if not is_filler:
            filtered_words.append(w)

    if not filtered_words:
        return {
            "clipStart": clip_start,
            "clipEnd": clip_end,
            "durationSeconds": clip_end - clip_start,
            "videoFiles": video_files,
            "words": [],
            "timeline": [],
        }

    # 2. Generate the compressed timeline
    timeline = []
    compressed_words = []
    rendered_cursor = 0.0
    current_segment_source_start = clip_start
    
    # We'll also treat the AI cuts as "virtual gaps" in the loop below
    for i in range(len(filtered_words)):
        w = filtered_words[i]
        w_start_source = w["start"]
        w_end_source = w["end"]
        
        # Calculate the gap before this word
        if i == 0:
            gap_duration = w_start_source - clip_start
        else:
            gap_duration = w_start_source - filtered_words[i-1]["end"]
            
        # If the gap is excessive (due to silence OR removed filler), perform jump cut
        if gap_duration > SILENCE_THRESHOLD:
            # Close previous segment
            source_end = w_start_source - gap_duration + (KEEP_SILENCE / 2.0)
            duration = source_end - current_segment_source_start
            
            if duration > 0:
                timeline.append({
                    "sourceStart": round(current_segment_source_start, 3),
                    "sourceEnd": round(source_end, 3),
                    "renderedStart": round(rendered_cursor, 3),
                    "renderedEnd": round(rendered_cursor + duration, 3),
                    "durationSeconds": round(duration, 3),
                })
                rendered_cursor += duration
            
            # Start new segment
            current_segment_source_start = w_start_source - (KEEP_SILENCE / 2.0)
            
        # Add word with its new rendered timestamp
        w_rendered_start = rendered_cursor + (w_start_source - current_segment_source_start)
        w_rendered_end = rendered_cursor + (w_end_source - current_segment_source_start)
        
        compressed_words.append({
            **w,
            "start": round(w_rendered_start, 3),
            "end": round(w_rendered_end, 3),
        })

    # Close the final segment
    final_source_end = clip_end
    final_duration = final_source_end - current_segment_source_start
    if final_duration > 0:
        timeline.append({
            "sourceStart": round(current_segment_source_start, 3),
            "sourceEnd": round(final_source_end, 3),
            "renderedStart": round(rendered_cursor, 3),
            "renderedEnd": round(rendered_cursor + final_duration, 3),
            "durationSeconds": round(final_duration, 3),
        })
        rendered_cursor += final_duration

    return {
        "clipStart": clip_start,
        "clipEnd": clip_end,
        "durationSeconds": round(rendered_cursor, 3),
        "videoFiles": video_files,
        "words": compressed_words,
        "timeline": timeline,
        "score": highlight.get("score", 0),
        "reason": highlight.get("reason", ""),
        "mode": highlight.get("mode", "multimodal"),
        "suggested_cuts": suggested_cuts,
    }


def render_clip(
    render_config: dict,
    clip_index: int,
    output_dir: str,
    remotion_root: str,
) -> str:
    """
    Write render_config.json and invoke npx remotion render for one clip.

    Args:
        render_config: Built by build_render_config()
        clip_index: 1-based index for output filename
        output_dir: Directory to write clip_XX.mp4 into
        remotion_root: Absolute path to the remotion/ folder

    Returns:
        str: Absolute path to the rendered MP4 file

    Raises:
        RuntimeError: If Remotion render fails
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    config_path = out_path / f"render_config_{clip_index:02d}.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"renderConfig": render_config}, f, indent=2)

    output_mp4 = out_path / f"clip_{clip_index:02d}.mp4"
    duration_frames = round(render_config["durationSeconds"] * 30)  # 30fps

    cmd = [
        "npx", "remotion", "render",
        "PodcastClip",
        str(output_mp4.absolute()),
        f"--entry-point=src/index.tsx",
        f"--props={config_path.absolute()}",
        f"--frames=0-{duration_frames - 1}",
        "--codec=h264",
        "--pixel-format=yuv420p",
        "--log=error",
    ]

    # Windows requires shell=True to find 'npx' command (npx.cmd)
    import platform
    is_windows = platform.system() == "Windows"

    result = subprocess.run(
        cmd,
        cwd=remotion_root,
        capture_output=True,
        text=True,
        shell=is_windows,
        timeout=600,  # 10 minute max per clip
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Remotion render failed for clip {clip_index}:\n"
            f"STDOUT: {result.stdout[-2000:]}\n"
            f"STDERR: {result.stderr[-2000:]}"
        )

    return str(output_mp4)


def render_all_clips(
    job_id: str,
    tmp_dir: str,
    camera_config_path: str | None,
    remotion_root: str,
) -> list[str]:
    """
    Full render orchestration for a single job.

    Loads highlights.json and transcript.json, builds a render_config per clip,
    triggers Remotion render for each, returns list of output MP4 paths.

    Args:
        job_id: UUID of the job
        tmp_dir: Base .tmp_processing directory path
        camera_config_path: Path to camera_config.json or None
        remotion_root: Absolute path to the Remotion project directory

    Returns:
        list[str]: Absolute paths to rendered MP4 clips
    """
    job_dir = Path(tmp_dir) / job_id
    clips_dir = job_dir / "clips"

    # Load pipeline outputs
    highlights = json.loads((job_dir / "highlights.json").read_text(encoding="utf-8"))
    transcript_words = json.loads((job_dir / "transcript.json").read_text(encoding="utf-8"))

    # Build video_files map from camera config
    # Paths are stored relative to 'remotion/public/' for use with staticFile()
    if camera_config_path and Path(camera_config_path).exists():
        raw_config = json.loads(Path(camera_config_path).read_text(encoding="utf-8"))
        video_files = {
            speaker: f"tmp/{job_id}/{filename}"
            for speaker, filename in raw_config.items()
        }
    else:
        # Fallback: all speakers → camera1.mp4
        video_files = {"DEFAULT": f"tmp/{job_id}/camera1.mp4"}

    output_paths = []
    total_clips = len(highlights)
    print(f"  🎬 Rendering {total_clips} clips...")

    for i, highlight in enumerate(highlights, start=1):
        print(f"    - Rendering clip {i}/{total_clips} ({highlight['end'] - highlight['start']:.1f}s)...")
        config = build_render_config(
            highlight=highlight,
            transcript_words=list(transcript_words),  # copy to avoid mutation
            video_files=video_files,
        )
        output_mp4 = render_clip(
            render_config=config,
            clip_index=i,
            output_dir=str(clips_dir),
            remotion_root=remotion_root,
        )
        print(f"      ✅ Saved to {Path(output_mp4).name}")
        output_paths.append(output_mp4)

    return output_paths
