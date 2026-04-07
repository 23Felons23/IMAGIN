# Requirements: Automated Podcast Pipeline

**Defined:** 2026-04-01
**Core Value:** Frictionlessly transform long-form multicam video audio into viral, ready-to-publish vertical clips with zero manual editing.

## v1 Requirements

### Interface & Upload

- [ ] **UI-01**: User can drag and drop multiple video files (multicam) into a web dashboard (SvelteKit)
- [ ] **UI-02**: User can select between "multimodal highlight extraction" and "topic-driven" modes
- [ ] **UI-03**: If topic-driven, user can input a text prompt
- [ ] **UI-04**: User can view a status queue of their processing videos
- [ ] **UI-05**: User can download the final rendered MP4 files

### Pipeline Processing

- [ ] **PROC-01**: System transcribes all input audio with timestamps using Whisper
- [ ] **PROC-02**: System automatically synchronizes multiple camera angles based on audio alignment
- [ ] **PROC-03**: System identifies the active speaker at any given moment
- [ ] **PROC-04**: System generates a combined transcript with speaker labels mapping to specific cameras

### AI Highlight Extraction

- [ ] **AI-01**: For multimodal mode, system identifies 10-30s highlights combining audio energy spikes and high-engagement transcript segments using LLM
- [ ] **AI-02**: For topic-driven mode, system extracts contiguous 10-30s chunks matching the user's prompt using LLM

### Dynamic Video Rendering

- [ ] **REND-01**: System vertically auto-crops the 16:9 video to 9:16, tracking the active speaker's face
- [ ] **REND-02**: System smoothly switches the active camera feed to the person who is speaking
- [ ] **REND-03**: System renders animated, bouncy, colored, word-by-word subtitles
- [ ] **REND-04**: System randomly assigns emojis to highly emotional words in the subtitles
- [ ] **REND-05**: System exports final video using Remotion programmatic rendering pipeline

## v2 Requirements

### Analytics & Social

- **SOC-01**: Automated direct publishing to TikTok/Instagram APIs
- **SOC-02**: Generation of meta descriptions and hashtags
- **SOC-03**: Webhooks for external automation (e.g., Make.com, Zapier)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user accounts / Auth | Local tool for single creator, keep it simple for now |
| Cinematic split-screen | Focusing explicitly on Hormozi-style vertical jump cuts |
| Manual timeline editing UI | Contradicts "zero manual editing" value prop |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 1 | Pending |
| UI-02 | Phase 1 | Pending |
| UI-03 | Phase 1 | Pending |
| UI-04 | Phase 1 | Pending |
| UI-05 | Phase 1 | Pending |
| PROC-01 | Phase 2 | Pending |
| PROC-02 | Phase 2 | Pending |
| PROC-03 | Phase 2 | Pending |
| PROC-04 | Phase 2 | Pending |
| AI-01 | Phase 3 | Pending |
| AI-02 | Phase 3 | Pending |
| REND-01 | Phase 4 | Pending |
| REND-02 | Phase 4 | Pending |
| REND-03 | Phase 4 | Pending |
| REND-04 | Phase 4 | Pending |
| REND-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after initial definition*
