/**
 * Stadium - Main entry point for all stadium components and utilities
 * 
 * Clean imports for the entire stadium module:
 * 
 * import { GameHeader, Scoreboard, GameInfo } from '@/components/stadium';
 * import { PitchZoneGrid } from '@/components/stadium';
 * import { COLORS, SPACING, TYPOGRAPHY } from '@/components/stadium';
 * import { useStadiumLayout } from '@/components/stadium';
 */

// Components
export {
  GameHeader,
  Scoreboard,
  GameInfo,
  PitchZoneGrid,
  PitchSelector,
  StrikeZoneGrid,
  GameStatsPanel,
  LineupPanel,
  StrikeoutCounter,
  TacticalHand,
  TacticalCardItem,
  SubmitPlayButton,
  CentralField,
} from './components';

// Types
export type {
  PlayerRole,
  PitchType,
  SwingType,
  PlayerData,
  PlayerStat,
  GameState,
  GameRunners,
  LineupPlayer,
  TeamData,
  TacticalCard,
  GameResult,
  InningCompleted,
  RarityConfig,
  // Props interfaces
  ScoreboardProps,
  GameInfoProps,
  GameHeaderProps,
  PlayerCardProps,
  PitchZoneGridProps,
  GameStatsPanelProps,
  TacticalHandProps,
  CentralFieldProps,
} from './types/stadium.types';

export { RarityLevel } from './types/stadium.types';

// Constants
export {
  COLORS,
  RARITY_COLORS,
  TYPOGRAPHY,
  SPACING,
  SIZES,
  ANIMATIONS,
  GAME_CONFIG,
  EFFECTS,
  BORDER_RADIUS,
  Z_INDEX,
  getRarityConfig,
  getRarityLabel,
  getOverlayDuration,
} from './constants/stadium.constants';

// Hooks
export {
  useStadiumLayout,
  useGameStateFormatting,
  usePlayerCardOptimization,
  useAnimationConfig,
  classNames,
  conditionalStyle,
} from './hooks/useStadiumLayout';
