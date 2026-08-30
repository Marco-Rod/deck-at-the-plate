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

// Components - Base stadium components
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
  PitcherStaminaBar,
} from './components';

// Components - Refactored screens
export { GameplayModals } from './GameplayModals';
export { GameplayInterface } from './GameplayInterface';
export { StadiumShowcaseScreen } from './StadiumShowcaseScreen';

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

// Hooks - Stadium Layout
export {
  useStadiumLayout,
  useGameStateFormatting,
  usePlayerCardOptimization,
  useAnimationConfig,
  classNames,
  conditionalStyle,
} from './hooks/useStadiumLayout';

// Hooks - Game Logic (imported from parent hooks directory)
export {
  useGameStateSetup,
  useModalSequencing,
  useCardLoading,
  useTacticalControls,
  useEventSequencerCallbacks,
} from '../../hooks';
