/**
 * Stadium Components - Main barrel exports
 * 
 * Use these imports for clean, maintainable code:
 * 
 * import { GameHeader, Scoreboard, GameInfo } from '@/components/stadium/components';
 * import { PitchZoneGrid } from '@/components/stadium/components';
 */

// Base Components
export { GameHeader } from './base';
export { Scoreboard } from './base';
export { GameInfo } from './base';

// Pitch Components
export { PitchZoneGrid, PitchSelector, StrikeZoneGrid } from './pitch';

// Stats Components
export { GameStatsPanel, LineupPanel, StrikeoutCounter } from './stats';

// Tactical Components
export { TacticalHand, TacticalCardItem, SubmitPlayButton } from './tactical';

// Layout Components
export { CentralField } from './layouts';

// Note: PlayerCard will be added as it's refactored
