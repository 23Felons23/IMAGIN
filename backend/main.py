import os
import uuid
import shutil
from pathlib import Path
from dotenv import load_dotenv

# NumPy 2.0 & PyTorch 2.6 Compatibility Bridge
import numpy as np
import torch

if not hasattr(np, "NaN"):
    np.NaN = np.nan
if not hasattr(np, "NAN"):
    np.NAN = np.nan
if not hasattr(np, "float_"):
    np.float_ = float

# Universal Fix: Globally allow loading all model weights (bypasses PyTorch 2.6+ restrictions)
original_torch_load = torch.load
def patched_torch_load(*args, **kwargs):
    kwargs["weights_only"] = False
    return original_torch_load(*args, **kwargs)
torch.load = patched_torch_load

# SpeechBrain Universal Fix: prevent crashes when optional integrations (k2, flair, etc.) are missing
try:
    import speechbrain.utils.importutils as sb_imp
    original_ensure = sb_imp.LazyModule.ensure_module
    def patched_ensure(self, stacklevel=1):
        try:
            return original_ensure(self, stacklevel + 1)
        except ImportError:
            from types import ModuleType
            dummy = ModuleType(self.target)
            dummy.__path__ = [] # Make it look like a package
            return dummy
    sb_imp.LazyModule.ensure_module = patched_ensure
except (ImportError, AttributeError, ModuleNotFoundError):
    pass

# HuggingFace Compatibility Fix: handle use_auth_token rename globally
try:
    import huggingface_hub
    
    def patch_hf_func(original_func):
        def patched_func(*args, **kwargs):
            if "use_auth_token" in kwargs:
                kwargs["token"] = kwargs.pop("use_auth_token")
            return original_func(*args, **kwargs)
        return patched_func

    huggingface_hub.hf_hub_download = patch_hf_func(huggingface_hub.hf_hub_download)
    huggingface_hub.model_info = patch_hf_func(huggingface_hub.model_info)
except (ImportError, AttributeError):
    pass

# Environment Injection: Ensure FFmpeg and NVIDIA libraries are in PATH
import os
from pathlib import Path

# 1. ADD FFmpeg
ffmpeg_full_path = os.environ.get("FFMPEG_PATH", "")
if ffmpeg_full_path:
    ffmpeg_dir = str(Path(ffmpeg_full_path).parent)
    if ffmpeg_dir not in os.environ["PATH"]:
        os.environ["PATH"] = ffmpeg_dir + os.path.pathsep + os.environ["PATH"]

# 2. ADD NVIDIA cuDNN/cuBLAS from venv
venv_site_packages = os.path.join(str(Path(__file__).parent), "venv", "Lib", "site-packages")
nvidia_paths = [
    os.path.join(venv_site_packages, "nvidia", "cudnn", "bin"),
    os.path.join(venv_site_packages, "nvidia", "cublas", "bin"),
]
for p in nvidia_paths:
    if os.path.exists(p) and p not in os.environ["PATH"]:
        os.environ["PATH"] = p + os.path.pathsep + os.environ["PATH"]

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

TMP_DIR = Path("../remotion/public/tmp")
TMP_DIR.mkdir(exist_ok=True)

# In-memory job store (replace with DB in future)
jobs: dict = {}


def run_full_pipeline(job_id: str, force_highlights: bool = False):
    """Full processing pipeline with resume logic and verbose logging."""
    try:
        print(f"\n🚀 [Job {job_id}] Starting pipeline...")
        job_dir = TMP_DIR / job_id
        video_path = str(job_dir / "camera1.mp4")
        master_wav = str(job_dir / "master.wav")
        mode = jobs[job_id].get("mode", "multimodal")
        topic = jobs[job_id].get("topic", "")

        # Phase 1: Audio extraction
        if not Path(master_wav).exists():
            jobs[job_id]["status"] = "extracting_audio"
            print(f"🔊 [Job {job_id}] Phase 1: Extracting master audio...")
            from audio_sync import extract_audio
            extract_audio(video_path, master_wav)
            print(f"✅ [Job {job_id}] Audio extracted to {master_wav}")
        else:
            print(f"⏩ [Job {job_id}] Phase 1 skipped: {master_wav} already exists.")

        # Phase 2: Transcription + diarization
        transcript_path = job_dir / "transcript.json"
        if not transcript_path.exists():
            jobs[job_id]["status"] = "transcribing"
            print(f"📝 [Job {job_id}] Phase 2: Transcribing and diarizing...")
            hf_token = os.environ.get("HF_TOKEN", "")
            from transcriber import transcribe_and_diarize
            transcript = transcribe_and_diarize(master_wav, hf_token)
            
            import json
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(transcript, f, indent=2)
            
            # Save a human-readable version for the user
            from highlight_extractor import _format_chunk_as_text
            transcript_md_path = job_dir / "transcript.md"
            readable_text = _format_chunk_as_text({"words": transcript, "chunk_start": transcript[0]["start"], "chunk_end": transcript[-1]["end"]})
            with open(transcript_md_path, "w", encoding="utf-8") as f:
                f.write(f"# Transcription Complète\n\n{readable_text}")
                
            print(f"✅ [Job {job_id}] Phase 2 complete. Words: {len(transcript)}")
        else:
            print(f"⏩ [Job {job_id}] Phase 2 skipped: {transcript_path} already exists.")
            with open(transcript_path, "r", encoding="utf-8") as f:
                import json
                transcript = json.load(f)

        # Phase 3: AI Highlight Extraction
        # We always rerun this if force_highlights is True OR if highlights.json doesn't exist
        highlights_json_path = job_dir / "highlights.json"
        if force_highlights or not highlights_json_path.exists():
            jobs[job_id]["status"] = "extracting_highlights"
            print(f"🧠 [Job {job_id}] Phase 3: Extracting AI highlights...")
            from highlight_extractor import extract_highlights_multimodal, extract_highlights_topic
            from highlight_serializer import save_highlights_json, save_highlights_markdown

            if mode == "topic" and topic:
                highlights = extract_highlights_topic(transcript_path=str(transcript_path), topic_prompt=topic)
            else:
                highlights = extract_highlights_multimodal(transcript_path=str(transcript_path), audio_path=master_wav)

            save_highlights_json(highlights, str(highlights_json_path))
            save_highlights_markdown(highlights, str(job_dir / "highlights.md"), mode=mode, topic_prompt=topic or None)
            print(f"✨ [Job {job_id}] Phase 3 complete. Highlights found: {len(highlights)}")
        else:
            print(f"⏩ [Job {job_id}] Phase 3 skipped: {highlights_json_path} already exists.")
            with open(highlights_json_path, "r", encoding="utf-8") as f:
                import json
                highlights = json.load(f)

        # Phase 4: Remotion Video Rendering
        jobs[job_id]["status"] = "rendering"
        print(f"🎬 [Job {job_id}] Phase 4: Rendering vertical clips with Remotion...")
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
        print(f"🏁 [Job {job_id}] PIPELINE COMPLETE. Rendered {len(output_clips)} clips.")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ [Job {job_id}] PIPELINE FAILED: {str(e)}")
        print(f"🔍 DEBUG TRACEBACK:\n{error_trace}")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"{str(e)}\n\nTraceback:\n{error_trace}"


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


@app.post("/api/jobs/{job_id}/rerun")
async def rerun_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    mode: str | None = None,
    topic: str | None = None,
    force_highlights: bool = True
):
    """
    Rerun an existing job. 
    Skips transcription if transcript.json already exists.
    Allows updating the mode or topic for debugging Phase 3.
    """
    if job_id not in jobs:
        # Check if directory exists even if not in memory (server restart)
        job_dir = TMP_DIR / job_id
        if not job_dir.exists():
            return {"error": "Job not found"}
        
        # Re-register the job in memory
        jobs[job_id] = {
            "status": "processing",
            "mode": mode or "multimodal",
            "topic": topic or "",
        }
    
    # Update job config if requested
    if mode:
        jobs[job_id]["mode"] = mode
    if topic:
        jobs[job_id]["topic"] = topic
    
    jobs[job_id]["status"] = "processing"
    jobs[job_id].pop("error", None) # Clear previous errors
    
    background_tasks.add_task(run_full_pipeline, job_id, force_highlights=force_highlights)
    return {"job_id": job_id, "status": "processing", "message": "Rerun triggered (Skipping transcription if possible)"}


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


from fastapi.responses import FileResponse

@app.get("/api/jobs/{job_id}/download/{clip_name}")
async def download_clip(job_id: str, clip_name: str):
    """Serve a rendered MP4 clip."""
    job_dir = TMP_DIR / job_id
    clip_path = job_dir / "clips" / clip_name
    if not clip_path.exists():
        return {"error": "Clip not found"}
    return FileResponse(path=str(clip_path), filename=clip_name, media_type="video/mp4")
