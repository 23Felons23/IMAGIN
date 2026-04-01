import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {WordEntry} from './types';
import {getEmojiForWord} from './emojis';

interface EmojiOverlayProps {
  words: WordEntry[];
}

const EMOJI_DURATION_FRAMES = 20; // total frames emoji is visible
const EMOJI_PEAK_FRAME = 8;      // frame at which scale peaks

export const EmojiOverlay: React.FC<EmojiOverlayProps> = ({words}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const currentTime = frame / fps;

  // Find active word
  const activeIndex = words.findIndex(
    (w) => currentTime >= w.start && currentTime <= w.end
  );

  if (activeIndex === -1) return null;

  const activeWord = words[activeIndex];
  const emoji = getEmojiForWord(activeWord.word);

  if (!emoji) return null;

  const wordStartFrame = Math.round(activeWord.start * fps);
  const framesSinceWordStart = frame - wordStartFrame;

  // Only show for EMOJI_DURATION_FRAMES after word starts
  if (framesSinceWordStart > EMOJI_DURATION_FRAMES) return null;

  // Scale: spring in, then hold
  const scaleSpring = spring({
    frame: framesSinceWordStart,
    fps,
    config: {
      damping: 8,
      stiffness: 300,
      mass: 0.3,
    },
    from: 0,
    to: 1.2,
  });

  // Clamp scale at 1.0 after peak
  const scale = Math.min(scaleSpring, 1.2);

  // Fade out after peak
  const opacity = interpolate(
    framesSinceWordStart,
    [0, EMOJI_PEAK_FRAME, EMOJI_DURATION_FRAMES],
    [0, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  // Float upward slightly as it fades
  const translateY = interpolate(
    framesSinceWordStart,
    [0, EMOJI_DURATION_FRAMES],
    [0, -30],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        // Position above subtitle block
        paddingBottom: 340,
        pointerEvents: 'none',
      }}
    >
      <span
        style={{
          fontSize: 108,
          lineHeight: 1,
          transform: `scale(${scale}) translateY(${translateY}px)`,
          opacity,
          display: 'inline-block',
          filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.5))',
        }}
      >
        {emoji}
      </span>
    </AbsoluteFill>
  );
};
