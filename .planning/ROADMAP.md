# Roadmap: Automated Podcast Pipeline

## Overview

We are building an automated podcast pipeline that transforms raw multicam video into ready-to-publish vertical clips with bouncing subtitles. We'll start by building the SvelteKit frontend dashboard, followed by the core Python audio/video processing and LLM highlight extraction backend, and finally integrate Remotion for dynamic video rendering.

## Phases

- [ ] **Phase 1: Interface & Upload (SvelteKit)** - Drag-and-drop dashboard for video upload and job queuing.
- [ ] **Phase 2: Pipeline Processing (Whisper)** - Audio synchronization, transcription, and active speaker identification.
- [ ] **Phase 3: AI Highlight Extraction (LLM)** - Multimodal energy and topic-driven highlight identification.
- [ ] **Phase 4: Dynamic Video Rendering (Remotion)** - Vertical cropping, speaker switching, and bouncy subtitle generation.

## Phase Details

### Phase 1: Interface & Upload (SvelteKit)
**Goal**: Establish the SvelteKit frontend where users can configure and upload videos for processing.
**Depends on**: Nothing
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria**:
  1. User can drag and drop multiple video files successfully.
  2. User can toggle between highlight extraction modes (multimodal vs topic-driven).
  3. Uploaded files are successfully queued for backend processing.
**Plans**: 2 plans

Plans:
- [ ] 01-01: Setup SvelteKit project, layout, and upload form components.
- [ ] 01-02: Implement job queuing (e.g., BullMQ) and status tracking backend routes.

### Phase 2: Pipeline Processing (Whisper)
**Goal**: Build the Python audio processing pipeline to align and transcribe multiple camera feeds.
**Depends on**: Phase 1
**Requirements**: PROC-01, PROC-02, PROC-03, PROC-04
**Success Criteria**:
  1. System extracts clear audio and aligns multiple video tracks.
  2. System generates accurate Whisper text transcripts with timestamps.
  3. System accurately identifies the active speaker corresponding to each camera.
**Plans**: 2 plans

Plans:
- [ ] 02-01: Implement audio alignment and combined transcript generation.
- [ ] 02-02: Implement active speaker diarization mapping to camera inputs.

### Phase 3: AI Highlight Extraction (LLM)
**Goal**: Use LLMs to determine the best 30-60 second clips using either energy or text topics.
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02
**Success Criteria**:
  1. System identifies 30-60s "highlights" matching user's text prompt.
  2. System identifies highlights using audio spikes + transcript engagement.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Build the multimodal highlight extractor using audio energy analysis and LLM sentiment.
- [ ] 03-02: Build the topic-driven highlight extractor using LLM context mapping.

### Phase 4: Dynamic Video Rendering (Remotion)
**Goal**: Render the final TikTok/Reels style vertical cut with bouncing subtitles.
**Depends on**: Phase 3
**Requirements**: REND-01, REND-02, REND-03, REND-04, REND-05
**Success Criteria**:
  1. Output video is cropped to 9:16 and automatically switches to the active speaker's camera.
  2. Subtitles bounce word-by-word accurately synced to the audio.
  3. Emojis appear alongside context-appropriate words.
**Plans**: 3 plans

Plans:
- [ ] 04-01: Setup Remotion components for vertical video layout and auto-camera switching sequence.
- [ ] 04-02: Implement dynamic, word-by-word colorful subtitle animations with randomized emojis.
- [ ] 04-03: Create the backend bridge connecting Python job outputs to the Remotion CLI renderer.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Interface & Upload (SvelteKit) | 0/2 | Not started | - |
| 2. Pipeline Processing (Whisper) | 0/2 | Not started | - |
| 3. AI Highlight Extraction (LLM) | 0/2 | Not started | - |
| 4. Dynamic Video Rendering (Remotion) | 0/3 | Not started | - |
