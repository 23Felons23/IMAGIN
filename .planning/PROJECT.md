

# Automated Podcast Pipeline

## What This Is

A web-based service (SvelteKit UI) that takes uploaded multicam podcast or interview video files and automatically detects, crops, edits, and adds subtitles to high-energy or topic-driven highlights. It targets creators who want to quickly generate dynamic, "Hormozi-style" vertical clips for TikTok and Instagram without manual labor.

## Core Value

Frictionlessly transform long-form multicam video audio into viral, ready-to-publish vertical clips with zero manual editing.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] SvelteKit drag-and-drop web dashboard for video and multi-cam uploads
- [ ] Topic-driven highlight extraction (using Whisper + LLM)
- [ ] Multimodal energy highlight extraction (audio spikes + transcript analysis)
- [ ] Automatic multi-camera syncing and visual switching (Speaker tracking)
- [ ] Vertical auto-cropping to active speaker
- [ ] Dynamic remotion rendering for rapid cuts and bouncy, word-by-word colorful subtitles with emojis
- [ ] Output ready-to-upload MP4s

### Out of Scope

- [ ] Cinematic or slow-paced split-screen editing — We are focusing purely on high-energy, vertical, rapid-cut TikTok/Reels style.
- [ ] Local CLI processing only — User opted for a full web interface to streamline creator experience.

## Context

- **Tech Environment:** SvelteKit frontend, Python pipeline (Whisper + LLMs for intelligence), Remotion for programmatic video rendering.
- **Goal:** Emulate the "Alex Hormozi" editing style programmatically without a human editor.
- **Inputs:** Separate camera files for Host/Guest which must be synced and switched correctly by identifying the active speaker.

## Constraints

- **Architecture**: Must separate the Python/AI processing from the Remotion rendering pipeline efficiently.
- **Performance**: Whisper and video rendering can be heavy; needs asynchronous task processing (e.g., job queues).
- **Design**: Output must match aggressive, fast-paced retention editing standards (Hormozi-style).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Web Service UI | Streamlines creator experience over bare CLI | — Pending |
| Remotion | Gives frame-perfect React control over animated bouncy subtitles | — Pending |
| Auto-Speaker Switching | Essential for dealing with separate camera tracks automatically | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-01 after initialization*
