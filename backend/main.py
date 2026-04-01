import os
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
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
    """Full processing pipeline: audio sync → transcription → diarization."""
    try:
        job_dir = TMP_DIR / job_id
        video_path = str(job_dir / "camera1.mp4")
        master_wav = str(job_dir / "master.wav")

        jobs[job_id]["status"] = "extracting_audio"

        # Phase 2: Audio extraction
        from audio_sync import extract_audio, find_audio_offset
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

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["transcript_path"] = str(transcript_path)

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.post("/api/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = TMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file in chunks to avoid memory blow-up
    dest = job_dir / "camera1.mp4"
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            out.write(chunk)

    jobs[job_id] = {"status": "processing", "filename": file.filename}
    background_tasks.add_task(run_full_pipeline, job_id)
    return {"job_id": job_id, "status": "processing"}


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
