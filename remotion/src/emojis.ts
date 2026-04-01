// Rule-based emoji keyword dictionary
// Matched case-insensitively against each spoken word

export const EMOJI_MAP: Record<string, string> = {
  // Money / wealth
  money: '💰',
  rich: '💰',
  wealth: '💰',
  millionaire: '💰',
  billionaire: '💰',
  profit: '💸',
  cash: '💸',
  pay: '💸',
  paid: '💸',

  // Energy / hype
  fire: '🔥',
  hot: '🔥',
  insane: '🤯',
  crazy: '🤯',
  wild: '🤯',
  unbelievable: '🤯',
  mindblowing: '🤯',
  wow: '😱',
  whoa: '😱',
  shocking: '😱',

  // Love / positivity
  love: '❤️',
  heart: '❤️',
  amazing: '🙌',
  incredible: '🙌',
  awesome: '🙌',
  beautiful: '🤩',
  perfect: '🤩',

  // Achievement / success
  win: '🏆',
  winner: '🏆',
  champion: '🏆',
  victory: '🏆',
  success: '🎯',
  goal: '🎯',
  achieve: '🎯',

  // Growth / momentum
  rocket: '🚀',
  launch: '🚀',
  growth: '📈',
  growing: '📈',
  rise: '📈',
  skyrocket: '🚀',

  // Religious / gratitude
  god: '🙏',
  pray: '🙏',
  grateful: '🙏',
  thankful: '🙏',
  blessed: '🙏',

  // Excellence
  hundred: '💯',
  percent: '💯',
  best: '💯',

  // Intelligence
  brain: '🧠',
  smart: '🧠',
  genius: '🧠',
  intelligence: '🧠',
  clever: '🧠',

  // Speed
  fast: '⚡',
  speed: '⚡',
  quick: '⚡',
  instant: '⚡',

  // Alert / stop
  stop: '🛑',
  wait: '✋',
  listen: '👂',
  important: '‼️',

  // Fun
  laugh: '😂',
  funny: '😂',
  joke: '😂',
  party: '🎉',
  celebrate: '🎉',
};

/**
 * Returns the emoji for a given word, or null if no match.
 * Strips punctuation before matching.
 */
export function getEmojiForWord(word: string): string | null {
  const normalized = word.toLowerCase().replace(/[^a-z]/g, '');
  return EMOJI_MAP[normalized] ?? null;
}
