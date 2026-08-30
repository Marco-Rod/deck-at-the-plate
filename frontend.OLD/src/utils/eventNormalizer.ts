/**
 * Event Normalizer
 * 
 * Normaliza nombres de eventos desde el backend al formato estándar (SNAKE_CASE).
 * Maneja variaciones como espacios, guiones, mayúsculas diferentes, etc.
 * 
 * Esto evita bugs donde el mismo evento llega con nombres diferentes
 * (ej: "HOME RUN" vs "HOME_RUN") y no se procesa correctamente.
 */

import { EVENT_SEQUENCES } from '../hooks/useEventSequencer';

/**
 * Mapeo exhaustivo de todas las variaciones de eventos posibles al nombre estándar.
 * Se actualiza según nuevos eventos del backend.
 */
const EVENT_MAPPINGS: Record<string, string> = {
  // HOME RUN variaciones
  'HOME RUN': 'HOME_RUN',
  'HOMERUN': 'HOME_RUN',
  'HOME_RUN': 'HOME_RUN',

  // STRIKEOUT variaciones
  'STRIKEOUT': 'STRIKEOUT',
  'STRIKE OUT': 'STRIKEOUT',
  'STRIKE-OUT': 'STRIKEOUT',
  'K': 'STRIKEOUT',

  // SINGLES/HITS
  'HIT_1B': 'HIT_1B',
  'HIT 1B': 'HIT_1B',
  '1B': 'HIT_1B',
  'SINGLE': 'HIT_1B',

  'HIT_2B': 'HIT_2B',
  'HIT 2B': 'HIT_2B',
  '2B': 'HIT_2B',
  'DOUBLE': 'HIT_2B',

  'HIT_3B': 'HIT_3B',
  'HIT 3B': 'HIT_3B',
  '3B': 'HIT_3B',
  'TRIPLE': 'HIT_3B',

  // OUTS
  'OUT_GROUND': 'OUT_GROUND',
  'OUT GROUND': 'OUT_GROUND',
  'OUT-GROUND': 'OUT_GROUND',
  'GROUND OUT': 'OUT_GROUND',
  'GROUNDOUT': 'OUT_GROUND',
  'GROUND-OUT': 'OUT_GROUND',
  'GROUND BALL': 'OUT_GROUND',

  'OUT_FLY': 'OUT_FLY',
  'OUT FLY': 'OUT_FLY',
  'OUT-FLY': 'OUT_FLY',
  'FLY OUT': 'OUT_FLY',
  'FLYOUT': 'OUT_FLY',
  'FLY-OUT': 'OUT_FLY',
  'FLY BALL': 'OUT_FLY',
  'OUT_FLYBALL': 'OUT_FLY',

  // WALKS
  'WALK': 'WALK',
  'BASE ON BALLS': 'WALK',
  'BB': 'WALK',
  'IBB': 'WALK',

  // FOULS
  'FOUL': 'FOUL',
  'FOUL BALL': 'FOUL',
  'FOUL-BALL': 'FOUL',
  'FOUL OUT': 'FOUL',

  // BALLS
  'BALL': 'BALL',

  // STRIKES
  'STRIKE_LOOKING': 'STRIKE_LOOKING',
  'STRIKE LOOKING': 'STRIKE_LOOKING',
  'STRIKE-LOOKING': 'STRIKE_LOOKING',
  'CALLED STRIKE': 'STRIKE_LOOKING',

  'STRIKE_SWINGING': 'STRIKE_SWINGING',
  'STRIKE SWINGING': 'STRIKE_SWINGING',
  'STRIKE-SWINGING': 'STRIKE_SWINGING',
  'SWINGING STRIKE': 'STRIKE_SWINGING',

  'STRIKE': 'STRIKE',

  // DOUBLE PLAY
  'DOUBLE_PLAY': 'DOUBLE_PLAY',
  'DOUBLE PLAY': 'DOUBLE_PLAY',
  'DOUBLE-PLAY': 'DOUBLE_PLAY',
  'DOUBLEPLAY': 'DOUBLE_PLAY',
  'DP': 'DOUBLE_PLAY',

  // PITCHER CHANGED
  'PITCHER_CHANGED': 'PITCHER_CHANGED',
  'PITCHER CHANGED': 'PITCHER_CHANGED',
  'PITCHER-CHANGED': 'PITCHER_CHANGED',

  // GAME OVER
  'GAME_OVER': 'GAME_OVER',
  'GAME OVER': 'GAME_OVER',
  'GAME-OVER': 'GAME_OVER',
};

/**
 * Normaliza un nombre de evento recibido del backend.
 * 
 * @param eventName - Nombre del evento del backend (puede tener espacios, guiones, etc)
 * @returns Nombre normalizado en SNAKE_CASE, listo para usar con EVENT_SEQUENCES
 * 
 * @example
 * normalizeEventName('HOME RUN') // → 'HOME_RUN'
 * normalizeEventName('ground out') // → 'OUT_GROUND'
 * normalizeEventName('STRIKE-LOOKING') // → 'STRIKE_LOOKING'
 */
export function normalizeEventName(eventName: string): string {
  if (!eventName) return '';

  // Convertir a mayúsculas y normalizar espacios iniciales/finales
  let normalized = eventName.toUpperCase().trim();

  // Intentar mapeo exacto primero
  if (EVENT_MAPPINGS[normalized]) {
    return EVENT_MAPPINGS[normalized];
  }

  // Si ya está en el formato estándar (con guion bajo), retornar como está
  if (Object.keys(EVENT_SEQUENCES).includes(normalized)) {
    return normalized;
  }

  // Convertir espacios a guiones bajos para casos que no estén mapeados
  normalized = normalized.replace(/\s+/g, '_');

  // También convertir guiones a guiones bajos
  normalized = normalized.replace(/-/g, '_');

  // Verificar si ahora está en EVENT_SEQUENCES
  if (Object.keys(EVENT_SEQUENCES).includes(normalized)) {
    return normalized;
  }

  // Si aún no coincide, loguear un warning con los eventos disponibles
  console.warn(
    `⚠️ [EVENT NORMALIZATION] Unknown event type: "${eventName}" → "${normalized}"\n` +
    `Available events: ${Object.keys(EVENT_SEQUENCES).join(', ')}`
  );

  return normalized;
}
