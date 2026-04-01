// Types shared across Remotion components

export interface WordEntry {
  word: string;
  start: number; // seconds relative to clip start
  end: number;   // seconds relative to clip start
  speaker: string;
}

export interface RenderConfig {
  clipStart: number;       // original video timestamp (for reference)
  clipEnd: number;
  durationSeconds: number;
  videoFiles: Record<string, string>; // speaker_label → absolute video path
  words: WordEntry[];
  score: number;
  reason: string;
}
