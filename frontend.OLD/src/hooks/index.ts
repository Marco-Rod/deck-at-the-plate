/**
 * Hooks - Main entry point for all custom hooks
 */

// Game state and setup hooks
export { useGameStateSetup } from './useGameStateSetup';
export { useModalSequencing } from './useModalSequencing';
export { useCardLoading } from './useCardLoading';
export { useTacticalControls } from './useTacticalControls';
export { useEventSequencerCallbacks } from './useEventSequencerCallbacks';

// Existing hooks
export { useStadiumSocket, parseStateData } from './useStadiumSocket';
export { useEventSequencer, EVENT_SEQUENCES, EVENT_DURATIONS } from './useEventSequencer';
