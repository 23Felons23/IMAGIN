import os
import uuid
import shutil
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, BackgroundTasks

# Load .env from the backend directory
load_dotenv(Path(__file__).parent / ".env")
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Podcast Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = Path(".tmp_processing")
TMP_DIR.mkdir(exist_ok=True)

# In-memory job store (replace with DB in future)
jobs: dict = {}


def run_full_pipeline(job_id: str):
    """Full processing pipeline: audio sync → transcription → diarization → highlight extraction."""
    try:
        job_dir = TMP_DIR / job_id
        video_path = str(job_dir / "camera1.mp4")
        master_wav = str(job_dir / "master.wav")
        mode = jobs[job_id].get("mode", "multimodal")
        topic = jobs[job_id].get("topic", "")

        jobs[job_id]["status"] = "extracting_audio"

        # Phase 2: Audio extraction
        from audio_sync import extract_audio
        extract_audio(video_path, master_wav)

        jobs[job_id]["status"] = "transcribing"

        # Phase 2: Transcription + diarization
        hf_token = os.environ.get("HF_TOKEN", "")
        from transcriber import transcribe_and_diarize
        transcript = transcribe_and_diarize(master_wav, hf_token)

        import json
        transcript_path = job_dir / "transcript.json"
        with open(transcript_path, "w") as f:
            json.dump(transcript, f, indent=2)

        jobs[job_id]["status"] = "extracting_highlights"

        # Phase 3: AI Highlight Extraction
        from highlight_extractor import extract_highlights_multimodal, extract_highlights_topic
        from highlight_serializer import save_highlights_json, save_highlights_markdown

        if mode == "topic" and topic:
            highlights = extract_highlights_topic(
                transcript_path=str(transcript_path),
                topic_prompt=topic,
            )
        else:
            highlights = extract_highlights_multimodal(
                transcript_path=str(transcript_path),
                audio_path=master_wav,
            )

        highlights_json_path = str(job_dir / "highlights.json")
        highlights_md_path = str(job_dir / "highlights.md")

        save_highlights_json(highlights, highlights_json_path)
        save_highlights_markdown(highlights, highlights_md_path, mode=mode, topic_prompt=topic or None)

        jobs[job_id]["status"] = "highlights_ready"
        jobs[job_id]["transcript_path"] = str(transcript_path)
        jobs[job_id]["highlights_path"] = highlights_json_path
        jobs[job_id]["highlights_md_path"] = highlights_md_path
        jobs[job_id]["clip_count"] = len(highlights)

        jobs[job_id]["status"] = "rendering"

        # Phase 4: Remotion Video Rendering
        from render_bridge import render_all_clips
        remotion_root = str(Path(__file__).parent.parent / "remotion")
        camera_config_path = str(job_dir / "camera_config.json")

        output_clips = render_all_clips(
            job_id=job_id,
            tmp_dir=str(TMP_DIR),
            camera_config_path=camera_config_path if (job_dir / "camera_config.json").exists() else None,
            remotion_root=remotion_root,
        )

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["clips"] = output_clips
        jobs[job_id]["clip_count"] = len(output_clips)

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.post("/api/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: str = "multimodal",
    topic: str = "",
):
    job_id = str(uuid.uuid4())
    job_dir = TMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file in chunks to avoid memory blow-up
    dest = job_dir / "camera1.mp4"
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            out.write(chunk)

    jobs[job_id] = {
        "status": "processing",
        "filename": file.filename,
        "mode": mode,
        "topic": topic,
    }
    background_tasks.add_task(run_full_pipeline, job_id)
    return {"job_id": job_id, "status": "processing", "mode": mode}


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    return {"job_id": job_id, **job}


@app.delete("/api/jobs/{job_id}/cleanup")
async def cleanup_job(job_id: str):
    job_dir = TMP_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)
    jobs.pop(job_id, None)
    return {"cleaned": True}


@app.post("/api/jobs/{job_id}/camera-config")
async def upload_camera_config(job_id: str, file: UploadFile = File(...)):
    """
    Upload a camera_config.json to map speaker labels to video files.

    Example JSON:
        {"SPEAKER_00": "camera1.mp4", "SPEAKER_01": "camera2.mp4"}

    Must be uploaded before the job reaches 'rendering' status.
    """
    job_dir = TMP_DIR / job_id
    if not job_dir.exists():
        return {"error": "Job not found"}
    dest = job_dir / "camera_config.json"
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {"uploaded": True, "job_id": job_id}


@app.get("/api/jobs/{job_id}/clips")
async def get_job_clips(job_id: str):
    """List the rendered clip paths for a completed job."""
    job = jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    if job.get("status") != "complete":
        return {"status": job.get("status"), "clips": []}
    return {"job_id": job_id, "clips": job.get("clips", []), "clip_count": job.get("clip_count", 0)}
