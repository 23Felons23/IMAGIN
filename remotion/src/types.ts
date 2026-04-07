// Types shared across Remotion components

export interface WordEntry {
  word: string;
  start: number; // seconds relative to clip start (after jump cuts)
  end: number;   // seconds relative to clip start (after jump cuts)
  speaker: string;
}

export interface TimelineSegment {
  sourceStart: number;      // seconds relative to original video start
  sourceEnd: number;        // seconds relative to original video start
  renderedStart: number;    // seconds relative to rendered clip start
  renderedEnd: number;      // seconds relative to rendered clip start
  durationSeconds: number;
}

export interface RenderConfig {
  clipStart: number;       // original video timestamp (for reference)
  clipEnd: number;
  durationSeconds: number; // total duration of the rendered clip (after jump cuts)
  videoFiles: Record<string, string>; // speaker_label → absolute video path
  words: WordEntry[];
  timeline: TimelineSegment[];
  score: number;
  reason: string;
}
