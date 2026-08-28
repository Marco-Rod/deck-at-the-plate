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
  team?: string; // ⭐ NUEVO: Nombre del equipo
  role: PlayerRole; // ⭐ NUEVO: Tipo de jugador (PITCHER o BATTER)
  rarity?: string; // ⭐ NUEVO: Rareza de la carta (DIAMOND, GOLD, SILVER, BRONZE, COMMON)
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
  totalInnings?: number;
  lastEvent?: string;
  isGameOver?: boolean;
  winnerMessage?: string;
  activePitcherId?: string;
  activeBatterId?: string;
  rivalTeamName?: string;
  state_data?: Record<string, unknown>;
  pitcher_strikeouts?: Record<string, number>; // {pitcher_id: strikeout_count}
  batter_stats?: Record<string, { at_bats: number; hits: number; doubles: number; triples: number; home_runs: number; rbi: number; runs: number; strikeouts: number; walks: number }>; // ⭐ NUEVO
  homeHits?: number; // ⭐ NUEVO: Total hits HOME team
  awayHits?: number; // ⭐ NUEVO: Total hits AWAY team
  inning_runs?: Record<string, number>; // ⭐ NUEVO: {"1_true": 2, "1_false": 1, "6_false": 2} = inning_is_top: runs
  active_pitcher?: PlayerData; // ⭐ NUEVO: Datos completos del pitcher (incluyendo rarity)
  active_batter?: PlayerData;  // ⭐ NUEVO: Datos completos del bateador (incluyendo rarity)
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
  inning_completed?: boolean;
  pitcher_strikeouts?: Record<string, number>;
  batter_stats?: Record<string, { at_bats: number; hits: number; doubles: number; triples: number; home_runs: number; rbi: number; runs: number; strikeouts: number; walks: number }>;
  home_hits?: number; // ⭐ NUEVO
  away_hits?: number; // ⭐ NUEVO
  inning_runs?: Record<string, number>; // ⭐ NUEVO: {"1_true": 2, "1_false": 1}
  active_pitcher?: PlayerData; // ⭐ NUEVO: Datos del pitcher para la tarjeta
  active_batter?: PlayerData;  // ⭐ NUEVO: Datos del bateador para la tarjeta
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