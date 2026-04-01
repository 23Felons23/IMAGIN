import React from 'react';
import {AbsoluteFill, OffthreadVideo, useCurrentFrame, useVideoConfig} from 'remotion';
import type {RenderConfig, WordEntry} from './types';
import {Subtitles} from './Subtitles';
import {EmojiOverlay} from './EmojiOverlay';

interface PodcastClipProps {
  renderConfig: RenderConfig | null;
}

/**
 * Determine which video file to show at the current frame.
 * Maps the active speaker at currentTime → their assigned video file.
 * Falls back to "DEFAULT" key or first available file if no match.
 */
function getActiveVideoFile(
  words: WordEntry[],
  videoFiles: Record<string, string>,
  currentTimeSec: number
): string {
  const activeWord = words.find(
    (w) => currentTimeSec >= w.start && currentTimeSec <= w.end
  );

  const speaker = activeWord?.speaker ?? 'DEFAULT';

  // Exact speaker match
  if (videoFiles[speaker]) return videoFiles[speaker];

  // DEFAULT fallback
  if (videoFiles['DEFAULT']) return videoFiles['DEFAULT'];

  // First available
  return Object.values(videoFiles)[0];
}

export const PodcastClip: React.FC<PodcastClipProps> = ({renderConfig}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  if (!renderConfig) {
    return (
      <AbsoluteFill style={{backgroundColor: '#000', alignItems: 'center', justifyContent: 'center'}}>
        <span style={{color: '#fff', fontSize: 32}}>No render config provided</span>
      </AbsoluteFill>
    );
  }

  const {words, videoFiles, clipStart} = renderConfig;
  const currentTimeSec = frame / fps;

  const activeVideoPath = getActiveVideoFile(words, videoFiles, currentTimeSec);

  return (
    <AbsoluteFill style={{backgroundColor: '#000', width, height}}>
      {/* Main video — fills frame, object-fit cover for vertical crop */}
      <AbsoluteFill>
        <OffthreadVideo
          src={activeVideoPath}
          startFrom={Math.round(clipStart * fps)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center center',
          }}
        />
      </AbsoluteFill>

      {/* Darkening vignette in lower third for subtitle readability */}
      <AbsoluteFill
        style={{
          background: 'linear-gradient(to bottom, transparent 50%, rgba(0,0,0,0.7) 80%, rgba(0,0,0,0.85) 100%)',
        }}
      />

      {/* Subtitles */}
      <Subtitles words={words} />

      {/* Emoji overlays */}
      <EmojiOverlay words={words} />
    </AbsoluteFill>
  );
};
