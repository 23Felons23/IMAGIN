# IMAGIN — Automated Podcast Pipeline

Transform your multicam podcast into viral vertical clips with one click.

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11 - 3.12** (Required for WhisperX compatibility)
- **Node.js 18+**
- **FFmpeg** (Must be in your system PATH)

### 2. Installation

```bash
# Install Remotion & Frontend dependencies
npm install --prefix remotion
npm install --prefix frontend

# Install Backend dependencies
pip install -r backend/requirements.txt
```

### 3. Running the Project

You need three terminal windows:

#### Window 1: Backend (Server)
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

#### Window 2: Frontend (UI)
```bash
cd frontend
npm run dev
```

#### Window 3: Remotion Studio (Preview)
```bash
cd remotion
npx remotion studio
```

## 📂 Project Structure

- `backend/`: FastAPI server handling audio sync, transcription, and highlight extraction.
- `frontend/`: SvelteKit dashboard for project management.
- `remotion/`: React-based programmatic video rendering engine.
- `.tmp_processing/`: (Ignored) Temporary directory for video/audio processing.

## 🔑 Environment Setup

Create a `backend/.env` file:
```env
HF_TOKEN=your_huggingface_token
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
```
