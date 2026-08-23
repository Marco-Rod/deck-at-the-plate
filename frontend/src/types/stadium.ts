/**
 * stadium.ts — Tipos del módulo de juego en tiempo real
 * =======================================================
 * Define todas las interfaces y tipos usados por los componentes del estadio
 * y el hook useStadiumSocket.
 *
 * Convención de PitchType:
 *   Se usan los códigos estándar de MLB/Statcast para mantener consistencia
 *   con el backend (calculator.py, schemas/game.py).
 *
 *   FF  = Four-Seam Fastball (Recta de 4 costuras)
 *   SL  = Slider
 *   CU  = Curveball
 *   CH  = Changeup
 *   IBB = Intentional Walk (Base intencional)
 *
 * Las etiquetas de display en español están en PITCH_TYPE_LABELS.
 */

export type PlayerRole = 'PITCHER' | 'BATTER';

/**
 * Tipos de lanzamiento — códigos MLB estándar.
 * Deben coincidir con los valores aceptados por el backend en PitchActionRequest.
 */
export type PitchType = 'FF' | 'SL' | 'CU' | 'CH' | 'IBB';

/**
 * Etiquetas de display para cada tipo de lanzamiento.
 * Usar en UI en lugar del código crudo.
 */
export const PITCH_TYPE_LABELS: Record<PitchType, string> = {
  FF:  'RECTA',
  SL:  'SLIDER',
  CU:  'CURVA',
  CH:  'CAMBIO',
  IBB: 'BASE INTENCIONAL',
};

export type CardRarity = 'DIAMOND' | 'GOLD' | 'SILVER' | 'BRONZE' | 'COMMON';

export interface PlayerStat {
  label: string;
  val: number;
}

export interface PlayerData {
  id: string;
  name: string;
  number: string;
  overall: number;
  position: string;
  photo: string;
  stats: PlayerStat[];
}

export interface TacticalCard {
  id: string;
  name: string;
  cost: number;
  desc: string;
  type: string;
  color: string;
  icon: string;
}

/**
 * Estado del juego recibido por WebSocket.
 * Mapeado desde los campos del GameSession del backend.
 */
export interface GameStateWS {
  /** Número de entrada actual (1-based) */
  currentInning: number;
  /** true = Alta (visitante batea), false = Baja (local batea) */
  isTopInning: boolean;
  homeScore: number;
  awayScore: number;
  balls: number;
  strikes: number;
  outs: number;
  /** Estado de las bases: null = vacía, string = ID del corredor */
  runners: { b1: string | null; b2: string | null; b3: string | null };
  /** Último evento registrado (ej. "HIT_1B", "STRIKEOUT") */
  lastEvent?: string;
  /** Si es true, el juego terminó */
  isGameOver?: boolean;
  /** Mensaje del ganador si el juego terminó */
  winnerMessage?: string;
}

/**
 * Payload del evento PLAY_RESOLVED emitido por el backend vía WebSocket.
 */
export interface PlayResolvedPayload {
  type: 'PLAY_RESOLVED';
  event: string;
  description: string;
  outs: number;
  balls: number;
  strikes: number;
  score_home: number;
  score_away: number;
  current_inning: number;
  is_top_inning: boolean;
  state_data: Record<string, unknown>;
}

/**
 * Payload del evento PITCH_COMMITTED emitido por el backend vía WebSocket.
 */
export interface PitchCommittedPayload {
  type: 'PITCH_COMMITTED';
  message: string;
  has_pitched: boolean;
}

/**
 * Payload del evento INIT_GAME_STATE emitido al conectarse al WebSocket.
 */
export interface InitGameStatePayload {
  type: 'INIT_GAME_STATE';
  game_id: string;
  state: Record<string, unknown>;
}
