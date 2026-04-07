import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {WordEntry} from './types';

interface SubtitlesProps {
  words: WordEntry[];
}

const FONT_SIZE = 72;
const ACCENT_COLOR = '#FF3366';
const TEXT_STROKE = '-3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000, 4px 4px 0 #000';

/**
 * Group words into phrases. A phrase ends if it reaches 7 words
 * or if a word ends with punctuation (. ! ?).
 */
function groupIntoPhrases(words: WordEntry[]): WordEntry[][] {
  const phrases: WordEntry[][] = [];
  let currentPhrase: WordEntry[] = [];

  for (const w of words) {
    currentPhrase.push(w);
    const wordText = w.word.trim();
    if (currentPhrase.length >= 7 || /[.!?]$/.test(wordText)) {
      phrases.push(currentPhrase);
      currentPhrase = [];
    }
  }

  if (currentPhrase.length > 0) {
    phrases.push(currentPhrase);
  }

  return phrases;
}

const Word: React.FC<{word: WordEntry; isActive: boolean}> = ({word, isActive}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const springValue = spring({
    frame: frame - Math.round(word.start * fps),
    fps,
    config: {
      damping: 10,
      stiffness: 200,
      mass: 0.4,
    },
    from: 1.0,
    to: 1.25, // Scale up slightly when active
  });

  return (
    <span
      style={{
        fontSize: FONT_SIZE,
        fontWeight: 900,
        fontFamily: "'Impact', 'Arial Black', sans-serif",
        color: isActive ? ACCENT_COLOR : 'white',
        textShadow: TEXT_STROKE,
        transform: isActive ? `scale(${springValue})` : 'scale(1)',
        display: 'inline-block',
        margin: '0 8px',
        lineHeight: 1.2,
      }}
    >
      {word.word.toUpperCase()}
    </span>
  );
};

export const Subtitles: React.FC<SubtitlesProps> = ({words}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const currentTime = frame / fps;

  // Group the flat word list into stable phrases
  const phrases = React.useMemo(() => groupIntoPhrases(words), [words]);

  // Find which phrase should be visible. 
  // Logic: Find the phrase that has started but hasn't been replaced by a newer one.
  const activePhraseIndex = phrases.findLastIndex((phrase) => {
    return currentTime >= phrase[0].start;
  });

  const activePhrase = activePhraseIndex !== -1 ? phrases[activePhraseIndex] : null;

  if (!activePhrase) return null;

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        paddingBottom: 200,
        paddingLeft: 40,
        paddingRight: 40,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          flexWrap: 'wrap',
          textAlign: 'center',
          maxWidth: '90%',
        }}
      >
        {activePhrase.map((w, i) => {
          const isActive = currentTime >= w.start && currentTime <= w.end;
          return <Word key={`${w.word}-${i}`} word={w} isActive={isActive} />;
        })}
      </div>
    </AbsoluteFill>
  );
};
