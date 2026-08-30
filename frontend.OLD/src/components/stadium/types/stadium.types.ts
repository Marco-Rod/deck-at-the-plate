/**
 * Stadium Components - Centralized Type Definitions
 * 
 * Este archivo contiene todas las interfaces y tipos compartidos
 * entre componentes del stadium para evitar duplicación y facilitar
 * el mantenimiento de la estructura de datos.
 */

// ============================================================================
// ENUMS & UNIONS
// ============================================================================

export type PlayerRole = 'PITCHER' | 'BATTER';
export type PitchType = string;
export type SwingType = 'NORMAL' | 'POWER' | 'TAKE' | 'BUNT';

export enum RarityLevel {
  DIAMOND = 'DIAMOND',
  GOLD = 'GOLD',
  SILVER = 'SILVER',
  BRONZE = 'BRONZE',
  COMMON = 'COMMON',
}

// ============================================================================
// PLAYER & CARD TYPES
// ============================================================================

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
  photo?: string;
  team?: string;
  repertoire?: PitchRepertoire[];
  stats: PlayerStat[];
}

export interface PitchRepertoire {
  pitch_type: string;
  velocity?: number;
  control?: number;
  movement?: number;
}

// ============================================================================
// GAME STATE
// ============================================================================

export interface GameRunners {
  b1: string | null;
  b2: string | null;
  b3: string | null;
}

export interface GameState {
  currentInning: number;
  isTopInning: boolean;
  homeScore: number;
  awayScore: number;
  balls: number;
  strikes: number;
  outs: number;
  runners: GameRunners;
  totalInnings?: number;
  lastEvent?: string;
  isGameOver?: boolean;
  winnerMessage?: string;
  activePitcherId?: string;
  activeBatterId?: string;
  rivalTeamName?: string;
  state_data?: Record<string, unknown>;
  pitcher_strikeouts?: Record<string, number>;
  batter_stats?: Record<string, BatterGameStats>;
  homeHits?: number;
  awayHits?: number;
  inning_runs?: Record<string, number>;
}

export interface BatterGameStats {
  at_bats: number;
  hits: number;
  doubles: number;
  triples: number;
  home_runs: number;
  rbi: number;
  runs: number;
  strikeouts: number;
  walks: number;
}

// ============================================================================
// LINEUP & TEAM DATA
// ============================================================================

export interface LineupPlayer {
  id?: string;
  name: string;
  number: string;
  photo?: string;
  overall?: number;
  position?: string;
}

export interface TeamData {
  id: string;
  name: string;
  short_name: string;
  logo?: string;
}

// ============================================================================
// TACTICAL CARDS
// ============================================================================

export interface TacticalCard {
  id: string;
  name: string;
  cost: number;
  desc: string;
  type: string;
  color: string;
  icon: string;
}

// ============================================================================
// GAME RESULTS & EVENTS
// ============================================================================

export interface GameResult {
  text: string;
  event?: string;
  ts: number;
}

export interface InningCompleted {
  visible: boolean;
  completedInning: number;
  completedHalf: 'TOP' | 'BOT';
  nextInning: number;
  nextHalf: 'TOP' | 'BOT';
}

// ============================================================================
// RARITY CONFIG
// ============================================================================

export interface RarityConfig {
  borderColor: string;
  shadowColor: string;
  glowColor: string;
}

// ============================================================================
// COMPONENT PROPS INTERFACES
// ============================================================================

export interface ScoreboardProps {
  gameState: GameState;
  role?: PlayerRole;
  userRole?: 'HOME' | 'AWAY';
  homeTeamName: string;
  awayTeamName: string;
  totalInnings?: number;
  homeHits?: number;
  awayHits?: number;
  inningRuns?: Record<string, number>;
}

export interface GameInfoProps {
  balls: number;
  strikes: number;
  outs: number;
  currentInning: number;
  totalInnings: number;
  isTopInning: boolean;
  role: PlayerRole;
  runners: GameRunners;
}

export interface GameHeaderProps {
  teamName?: string;
  isConnected: boolean;
  onBack: () => void;
}

export interface PlayerCardProps {
  player: PlayerData | null;
  role: PlayerRole;
  disableEffects?: boolean;
  disablePulse?: boolean;
}

export interface PitchZoneGridProps {
  role: PlayerRole;
  selectedZone: number;
  selectedPitch: PitchType;
  onSelectZone: (zone: number) => void;
  onSelectPitch: (pitch: PitchType) => void;
  repertoire?: PitchRepertoire[];
  disabled?: boolean;
}

export interface GameStatsPanelProps {
  lineup: LineupPlayer[];
  stats: Record<string, BatterGameStats>;
  isPitcher: boolean;
  pitcherStrikeouts?: number;
  pitcherName?: string;
  animateStrikeout?: boolean;
}

export interface TacticalHandProps {
  tacticalHand: TacticalCard[];
  selectedTacticalId: string | null;
  role: PlayerRole;
  isIBB: boolean;
  disabled: boolean;
  onSelectTactical: (id: string) => void;
  onSubmitPlay: () => void;
}

export interface CentralFieldProps {
  role: PlayerRole;
  pitcherCard: PlayerData | null;
  batterCard: PlayerData | null;
  selectedZone: number;
  selectedPitch: PitchType;
  repertoire?: PitchRepertoire[];
  hasPitched: boolean;
  isAwaitingResult: boolean;
  inningTransition: InningCompleted | null;
  onSelectZone: (zone: number) => void;
  onSelectPitch: (pitch: PitchType) => void;
  // ⭐ NEW: Game state for GameInfo
  balls?: number;
  strikes?: number;
  outs?: number;
  currentInning?: number;
  totalInnings?: number;
  isTopInning?: boolean;
  runners?: { b1: string | null; b2: string | null; b3: string | null };
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type Dict<T> = Record<string, T>;
