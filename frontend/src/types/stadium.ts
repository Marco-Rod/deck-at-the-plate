// src/types/stadium.ts

export type PlayerRole = 'PITCHER' | 'BATTER';

export type PitchType = string;

/**
 * Mapa de etiquetas descriptivas para renderizar en UI
 */
export const PITCH_TYPE_LABELS: Record<string, string> = {
  '4-SEAM': 'RECTA (4-SEAM)',
  'SLIDER': 'SLIDER',
  'CURVE':  'CURVA',
  'CHANGE': 'CAMBIO',
  'FF':     'RECTA',
  'SL':     'SLIDER',
  'CU':     'CURVA',
  'CH':     'CAMBIO',
  'IBB':    'BASE INTENCIONAL',
};

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
  repertoire?: { pitch_type: string; velocity: number; control: number; movement: number }[];
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

export interface GameStateWS {
  currentInning: number;
  isTopInning: boolean;
  homeScore: number;
  awayScore: number;
  balls: number;
  strikes: number;
  outs: number;
  runners: { b1: string | null; b2: string | null; b3: string | null };
  lastEvent?: string;
  isGameOver?: boolean;
  winnerMessage?: string;
  activePitcherId?: string;
  activeBatterId?: string;
}

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

export interface PitchCommittedPayload {
  type: 'PITCH_COMMITTED';
  message: string;
  has_pitched: boolean;
}

export interface InitGameStatePayload {
  type: 'INIT_GAME_STATE';
  game_id: string;
  outs: number;
  balls: number;
  strikes: number;
  score_home: number;
  score_away: number;
  current_inning: number;
  is_top_inning: boolean;
  state_data: Record<string, unknown>;
}