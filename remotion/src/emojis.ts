// Rule-based emoji keyword dictionary
// Matched case-insensitively against each spoken word

export const EMOJI_MAP: Record<string, string> = {
  // Money / wealth
  money: '💰',
  rich: '💰',
  wealth: '💰',
  argent: '💰',
  riche: '💰',
  profit: '💸',
  cash: '💸',
  pay: '💸',
  paid: '💸',

  // Energy / hype
  fire: '🔥',
  hot: '🔥',
  feu: '🔥',
  chaud: '🔥',
  insane: '🤯',
  crazy: '🤯',
  wild: '🤯',
  dingue: '🤯',
  fou: '🤯',
  incroyable: '🤯',
  wow: '😱',
  whoa: '😱',

  // Love / positivity
  love: '❤️',
  heart: '❤️',
  amour: '❤️',
  coeur: '❤️',
  amazing: '🙌',
  incredible: '🙌',
  genial: '🙌',
  top: '🙌',
  parfait: '🤩',

  // Achievement / success
  win: '🏆',
  winner: '🏆',
  champion: '🏆',
  victoire: '🏆',
  success: '🎯',
  reussite: '🎯',
  but: '🎯',

  // Growth / momentum
  rocket: '🚀',
  fusée: '🚀',
  launch: '🚀',
  lancement: '🚀',
  growth: '📈',
  croissance: '📈',

  // Religious / gratitude
  god: '🙏',
  dieu: '🙏',
  merci: '🙏',
  grandiose: '🙏',

  // Excellence
  hundred: '💯',
  percent: '💯',
  cent: '💯',
  best: '💯',
  meilleur: '💯',

  // Intelligence
  brain: '🧠',
  cerveau: '🧠',
  smart: '🧠',
  intelligent: '🧠',
  genius: '🧠',
  genie: '🧠',

  // Speed
  fast: '⚡',
  rapide: '⚡',
  vitesse: '⚡',
  vite: '⚡',

  // Alert / stop
  stop: '🛑',
  attends: '✋',
  ecoute: '👂',
  important: '‼️',

  // Fun
  laugh: '😂',
  funny: '😂',
  drôle: '😂',
  rire: '😂',
  party: '🎉',
  fete: '🎉',
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
