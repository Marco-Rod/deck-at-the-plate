/**
 * GameStatsPanel - Main stats display component
 * 
 * Dual-mode component that displays either:
 * 1. LineupPanel (isPitcher=false) - Shows batting lineup with stats
 * 2. StrikeoutCounter (isPitcher=true) - Shows pitcher's strikeout count
 * 
 * Propuesta 1: Replaces separate panels with unified, well-organized component
 * 
 * @component
 * @example
 * // Lineup Mode
 * <GameStatsPanel
 *   lineup={players}
 *   stats={batterStats}
 *   isPitcher={false}
 * />
 * 
 * // Strikeout Mode
 * <GameStatsPanel
 *   lineup={[]}
 *   stats={{}}
 *   isPitcher={true}
 *   pitcherStrikeouts={5}
 *   pitcherName=\"David Romular\"
 * />
 */

import React from 'react';
import type { GameStatsPanelProps } from '../../types/stadium.types';
import { LineupPanel } from './LineupPanel';
import { StrikeoutCounter } from './StrikeoutCounter';

export const GameStatsPanel: React.FC<GameStatsPanelProps> = ({
  lineup,
  stats,
  isPitcher,
  pitcherStrikeouts = 0,
  pitcherName = 'Pitcher',
  animateStrikeout = false,
}) => {
  /**
   * Render appropriate panel based on isPitcher mode
   */
  if (isPitcher) {
    // RIGHT PANEL: STRIKEOUT COUNTER
    return (
      <StrikeoutCounter
        strikeouts={pitcherStrikeouts}
        pitcherName={pitcherName}
        animate={animateStrikeout}
      />
    );
  }

  // LEFT PANEL: LINEUP
  return (
    <LineupPanel
      lineup={lineup}
      stats={stats}
      pitcherName={pitcherName}
    />
  );
};

GameStatsPanel.displayName = 'GameStatsPanel';
