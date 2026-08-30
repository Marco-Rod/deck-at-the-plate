/**
 * LineupPanel - Simple batting lineup display
 * 
 * Diseño estilo lista de alineación profesional:
 * - Items: número, nombre, stats (AB-H)
 * - Separadores entre jugadores
 * - Scrollable, grande y legible
 * 
 * @component
 * @example
 * <LineupPanel
 *   lineup={lineupPlayers}
 *   stats={batterStats}
 * />
 */

import React from 'react';
import type { LineupPlayer, BatterGameStats } from '../../types/stadium.types';

interface LineupPanelProps {
  lineup: LineupPlayer[];
  stats: Record<string, BatterGameStats>;
  pitcherName?: string;
}

export const LineupPanel: React.FC<LineupPanelProps> = ({
  lineup,
  stats,
  pitcherName = 'Pitcher',
}) => {
  return (
    <div className="bg-[#0A0D0F]/95 border border-[#C5A059]/30 rounded-sm p-0 h-full flex flex-col overflow-hidden">
      {/* LINEUP ITEMS - SCROLLABLE */}
      <div className="flex-1 overflow-y-auto">
        {lineup && lineup.length > 0 ? (
          lineup.map((player, idx) => {
            const playerStats = stats[player.id || ''] as BatterGameStats | undefined;
            const abh = playerStats 
              ? `${playerStats.at_bats}-${playerStats.hits}` 
              : '0-0';

            // ⭐ NUEVO: Obtener solo stats > 0
            const activeStats = playerStats ? [
              playerStats.hits > 0 && `H:${playerStats.hits}`,
              playerStats.home_runs > 0 && `HR:${playerStats.home_runs}`,
              playerStats.walks > 0 && `BB:${playerStats.walks}`,
              playerStats.rbi > 0 && `RBI:${playerStats.rbi}`,
              playerStats.runs > 0 && `R:${playerStats.runs}`,
              playerStats.strikeouts > 0 && `SO:${playerStats.strikeouts}`,
            ].filter(Boolean) : [];

            return (
              <div key={player.id || idx}>
                {/* Player Row - Number + Name + AB-H + Active Stats */}
                <div className="flex items-center justify-between px-4 py-1.5 text-[13px] font-mono text-[#F7F5F0] hover:bg-[#1A3323]/30 transition-colors gap-2">
                  {/* Number */}
                  <span className="text-[#C5A059] font-bold w-5 text-right flex-shrink-0">
                    {idx + 1}
                  </span>
                  
                  {/* Name */}
                  <span className="font-bold px-2 flex-shrink-0 min-w-0">
                    {player.name}
                  </span>

                  {/* AB-H */}
                  <span className="text-[#C5A059] font-bold flex-shrink-0">
                    {abh}
                  </span>

                  {/* ⭐ NUEVO: Active Stats as badges */}
                  <div className="flex gap-1 flex-shrink-0 ml-auto">
                    {activeStats.map((stat, i) => (
                      <span key={i} className="text-[10px] text-[#C5A059]/80 bg-[#1A3323]/40 px-1.5 py-0.5 rounded whitespace-nowrap">
                        {stat}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Separator */}
                {idx < lineup.length - 1 && (
                  <div className="border-t border-[#C5A059]/10" />
                )}
              </div>
            );
          })
        ) : (
          <div className="text-[#C5A059]/60 text-[12px] text-center py-8 flex items-center justify-center h-full">
            No lineup data
          </div>
        )}
      </div>
    </div>
  );
};

LineupPanel.displayName = 'LineupPanel';
