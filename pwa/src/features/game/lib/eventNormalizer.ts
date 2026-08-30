import { EVENT_SEQUENCES } from '@/features/game/hooks/useEventSequencer'

const EVENT_MAPPINGS: Record<string, string> = {
  'HOME RUN': 'HOME_RUN',
  HOMERUN: 'HOME_RUN',
  HOME_RUN: 'HOME_RUN',

  STRIKEOUT: 'STRIKEOUT',
  'STRIKE OUT': 'STRIKEOUT',
  'STRIKE-OUT': 'STRIKEOUT',
  K: 'STRIKEOUT',

  HIT_1B: 'HIT_1B',
  'HIT 1B': 'HIT_1B',
  '1B': 'HIT_1B',
  SINGLE: 'HIT_1B',

  HIT_2B: 'HIT_2B',
  'HIT 2B': 'HIT_2B',
  '2B': 'HIT_2B',
  DOUBLE: 'HIT_2B',

  HIT_3B: 'HIT_3B',
  'HIT 3B': 'HIT_3B',
  '3B': 'HIT_3B',
  TRIPLE: 'HIT_3B',

  OUT_GROUND: 'OUT_GROUND',
  'OUT GROUND': 'OUT_GROUND',
  'OUT-GROUND': 'OUT_GROUND',
  'GROUND OUT': 'OUT_GROUND',
  GROUNDOUT: 'OUT_GROUND',
  'GROUND-OUT': 'OUT_GROUND',
  'GROUND BALL': 'OUT_GROUND',

  OUT_FLY: 'OUT_FLY',
  'OUT FLY': 'OUT_FLY',
  'OUT-FLY': 'OUT_FLY',
  'FLY OUT': 'OUT_FLY',
  FLYOUT: 'OUT_FLY',
  'FLY-OUT': 'OUT_FLY',
  'FLY BALL': 'OUT_FLY',
  OUT_FLYBALL: 'OUT_FLY',

  WALK: 'WALK',
  'BASE ON BALLS': 'WALK',
  BB: 'WALK',
  IBB: 'WALK',

  FOUL: 'FOUL',
  'FOUL BALL': 'FOUL',
  'FOUL-BALL': 'FOUL',
  'FOUL OUT': 'FOUL',

  BALL: 'BALL',

  STRIKE_LOOKING: 'STRIKE_LOOKING',
  'STRIKE LOOKING': 'STRIKE_LOOKING',
  'STRIKE-LOOKING': 'STRIKE_LOOKING',
  'CALLED STRIKE': 'STRIKE_LOOKING',

  STRIKE_SWINGING: 'STRIKE_SWINGING',
  'STRIKE SWINGING': 'STRIKE_SWINGING',
  'STRIKE-SWINGING': 'STRIKE_SWINGING',
  'SWINGING STRIKE': 'STRIKE_SWINGING',

  STRIKE: 'STRIKE',

  DOUBLE_PLAY: 'DOUBLE_PLAY',
  'DOUBLE PLAY': 'DOUBLE_PLAY',
  'DOUBLE-PLAY': 'DOUBLE_PLAY',
  DOUBLEPLAY: 'DOUBLE_PLAY',
  DP: 'DOUBLE_PLAY',

  PITCHER_CHANGED: 'PITCHER_CHANGED',
  'PITCHER CHANGED': 'PITCHER_CHANGED',
  'PITCHER-CHANGED': 'PITCHER_CHANGED',

  GAME_OVER: 'GAME_OVER',
  'GAME OVER': 'GAME_OVER',
  'GAME-OVER': 'GAME_OVER',
}

export function normalizeEventName(eventName: string): string {
  if (!eventName) return ''

  let normalized = eventName.toUpperCase().trim()

  const mapped = EVENT_MAPPINGS[normalized]
  if (mapped) {
    return mapped
  }

  if (normalized in EVENT_SEQUENCES) {
    return normalized
  }

  normalized = normalized.replace(/\s+/g, '_').replace(/-/g, '_')

  if (normalized in EVENT_SEQUENCES) {
    return normalized
  }

  console.warn(
    `[EVENT NORMALIZATION] Unknown event type: "${eventName}" → "${normalized}"\n` +
      `Available events: ${Object.keys(EVENT_SEQUENCES).join(', ')}`,
  )

  return normalized
}