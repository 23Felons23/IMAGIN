# Summary: 04-01 Remotion Project Setup & Vertical Layout Component

- **Status**: Complete
- **Self-Check**: PASSED

## Deliverables
- `remotion/package.json`
- `remotion/tsconfig.json`
- `remotion/remotion.config.ts`
- `remotion/src/types.ts`
- `remotion/src/PodcastClip.tsx`
- `remotion/src/index.tsx`

## What was built
Remotion project scaffolded at `remotion/` with 1080×1920 (9:16) composition at 30fps. `PodcastClip.tsx` is the main composition component: uses `useCurrentFrame()` to compute current time in seconds, maps active speaker at that time frame against `videoFiles` config, renders the correct camera via `OffthreadVideo` with `object-fit: cover` for vertical fill. Vignette gradient overlay in lower third for subtitle readability. Children: `<Subtitles>` and `<EmojiOverlay>`. Shared types in `types.ts`.
