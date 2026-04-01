import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {WordEntry} from './types';

interface SubtitlesProps {
  words: WordEntry[];
}

const CONTEXT_WORD_COUNT = 4; // words to show before active word
const FONT_SIZE_ACTIVE = 72;
const FONT_SIZE_CONTEXT = 58;
const ACCENT_COLOR = '#FF3366';
const TEXT_STROKE = '-3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000, 4px 4px 0 #000';

export const Subtitles: React.FC<SubtitlesProps> = ({words}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const currentTime = frame / fps;

  // Find active word index
  const activeIndex = words.findIndex(
    (w) => currentTime >= w.start && currentTime <= w.end
  );

  if (activeIndex === -1) return null;

  const activeWord = words[activeIndex];

  // Spring animation starts at the frame when this word begins
  const wordStartFrame = Math.round(activeWord.start * fps);
  const springValue = spring({
    frame: frame - wordStartFrame,
    fps,
    config: {
      damping: 10,
      stiffness: 200,
      mass: 0.4,
    },
    from: 0.5,
    to: 1.0,
  });

  // Context: a few previous words
  const contextStart = Math.max(0, activeIndex - CONTEXT_WORD_COUNT);
  const contextWords = words.slice(contextStart, activeIndex);

  // Group context words into lines of ~5
  const wordsPerLine = 5;
  const contextLines: WordEntry[][] = [];
  for (let i = 0; i < contextWords.length; i += wordsPerLine) {
    contextLines.push(contextWords.slice(i, i + wordsPerLine));
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        paddingBottom: 140,
        paddingLeft: 40,
        paddingRight: 40,
      }}
    >
      <div style={{textAlign: 'center', width: '100%'}}>
        {/* Context words (previous) */}
        {contextLines.map((line, lineIdx) => (
          <div
            key={lineIdx}
            style={{
              display: 'flex',
              justifyContent: 'center',
              flexWrap: 'wrap',
              gap: 8,
              marginBottom: 4,
            }}
          >
            {line.map((w, i) => {
              const fadeOpacity = interpolate(
                activeIndex - (contextStart + lineIdx * wordsPerLine + i),
                [0, CONTEXT_WORD_COUNT],
                [0.8, 0.25],
                {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
              );
              return (
                <span
                  key={i}
                  style={{
                    fontSize: FONT_SIZE_CONTEXT,
                    fontWeight: 900,
                    fontFamily: "'Impact', 'Arial Black', sans-serif",
                    color: 'white',
                    opacity: fadeOpacity,
                    textShadow: TEXT_STROKE,
                    lineHeight: 1.1,
                  }}
                >
                  {w.word}
                </span>
              );
            })}
          </div>
        ))}

        {/* Active word — bouncy, accent color */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            marginTop: 4,
          }}
        >
          <span
            style={{
              fontSize: FONT_SIZE_ACTIVE,
              fontWeight: 900,
              fontFamily: "'Impact', 'Arial Black', sans-serif",
              color: ACCENT_COLOR,
              textShadow: TEXT_STROKE,
              transform: `scale(${springValue})`,
              display: 'inline-block',
              lineHeight: 1.1,
            }}
          >
            {activeWord.word.toUpperCase()}
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
