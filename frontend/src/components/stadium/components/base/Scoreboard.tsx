/**
 * Scoreboard - MLB-style game score display
 * 
 * Diseño estilo MLB (Major League Baseball):
 * - Header: INNING (1-9) + R H E columns
 * - Rows: Team name + Score + Inning runs + Totals (R, H, E)
 * - Horizontal layout, compact y profesional
 * 
 * @component
 * @example
 * <Scoreboard 
 *   gameState={gameState}
 *   homeTeamName="AXOLOTES"
 *   awayTeamName="YANKEES (CPU)"
 *   homeHits={5}
 *   awayHits={3}
 * />
 */

import React, { useEffect } from 'react';

interface ScoreboardProps {
  gameState?: any;
  userRole?: string;
  homeTeamName: string;
  awayTeamName: string;
  totalInnings?: number;
  homeHits?: number;
  awayHits?: number;
  inningRuns?: Record<string, number>;
  responsive?: boolean;
  compact?: boolean;
}

export const Scoreboard: React.FC<ScoreboardProps> = ({
  gameState,
  userRole,
  homeTeamName,
  awayTeamName,
  totalInnings = 9,
  homeHits = 0,
  awayHits = 0,
  inningRuns = {},
  responsive = true,
  compact = false,
}) => {
  const homeScore = gameState?.homeScore ?? 0;
  const awayScore = gameState?.awayScore ?? 0;
  const isTopInning = gameState?.isTopInning ?? true;
  const currentInning = gameState?.currentInning ?? 1;

  // Determine display mode
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const displayInnings = compact ? Math.min(5, totalInnings) : totalInnings;
  
  // Dynamic font sizes based on responsive prop
  const inningHeaderSize = compact ? 'text-[8px]' : 'text-[9px] sm:text-[10px] md:text-[11px]';
  const inningDataSize = compact ? 'text-[11px]' : 'text-[11px] sm:text-[12px] md:text-[14px]';
  const teamNameSize = compact ? 'text-[9px]' : 'text-[10px] sm:text-[11px] md:text-[13px]';
  const scoreSize = compact ? 'text-[13px]' : 'text-[14px] sm:text-[16px] md:text-[18px]';

  // Dynamic widths
  const teamNameWidth = compact ? 'w-28' : 'w-32 sm:w-40 md:w-60';
  const inningColWidth = compact ? 'w-5' : 'w-6 sm:w-7 md:w-9';
  const totalColWidth = compact ? 'w-7' : 'w-8 sm:w-9 md:w-11';

  // ⭐ DEBUG: Monitorear cambios en props - COMENTADO (ya verificado, funciona correctamente)
  // useEffect(() => {
  //   console.log('🎯 [SCOREBOARD] Props actualizado:');
  //   console.log('  - homeScore (total):', homeScore);
  //   console.log('  - awayScore (total):', awayScore);
  //   console.log('  - inningRuns COMPLETO:', inningRuns);
  //   console.log('  - inningRuns JSON:', JSON.stringify(inningRuns));
  //   console.log('  - inningRuns keys:', Object.keys(inningRuns));
  //   console.log('  - inningRuns values:', Object.values(inningRuns));
  //   
  //   // Mostrar cada clave individualmente
  //   Object.entries(inningRuns).forEach(([key, value]) => {
  //     console.log(`    ${key} → ${value}`);
  //   });
  // }, [homeScore, awayScore, inningRuns]);

  return (
    <div className="w-full bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded-sm overflow-x-auto">
      {/* HEADER ROW */}
      <div className="flex items-center bg-[#0A0D0F] border-b border-[#C5A059]/20 px-2 sm:px-3 md:px-4 py-1 md:py-2 min-w-max">
        {/* INNING label */}
        <div className={`${teamNameWidth} text-left flex-shrink-0`}>
          <span className={`font-mono ${inningHeaderSize} text-[#C5A059] uppercase font-bold tracking-wider`}>
            {compact ? 'INN' : 'INNING'}
          </span>
        </div>

        {/* Inning columns (1-9 or 1-5 on compact) */}
        <div className="flex gap-0.5 sm:gap-1 md:gap-3 flex-1">
          {Array.from({ length: displayInnings }).map((_, idx) => (
            <div
              key={`header-inning-${idx + 1}`}
              className={`${inningColWidth} text-center flex-shrink-0`}
            >
              <span className={`font-mono ${inningHeaderSize} text-[#E6DFD3] font-bold`}>
                {idx + 1}
              </span>
            </div>
          ))}
        </div>

        {/* R H E columns */}
        <div className="flex gap-0.5 sm:gap-2 md:gap-4 ml-1 sm:ml-2 md:ml-4 flex-shrink-0">
          {['R', 'H', 'E'].map((col) => (
            <div key={col} className={`${totalColWidth} text-center`}>
              <span className={`font-mono ${inningHeaderSize} text-[#E6DFD3] font-bold`}>
                {col}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* AWAY TEAM ROW - ARRIBA */}
      <div className="flex items-center px-2 sm:px-3 md:px-4 py-1 md:py-2 bg-[#1A3323]/30 border-b border-[#C5A059]/10 min-w-max">
        {/* Team name */}
        <div className={`${teamNameWidth} truncate flex-shrink-0`}>
          <span className={`font-mono ${teamNameSize} text-[#F7F5F0] uppercase font-bold tracking-wider`}>
            {compact ? awayTeamName.substring(0, 4) : awayTeamName}
          </span>
        </div>

        {/* Inning runs */}
        <div className="flex gap-0.5 sm:gap-1 md:gap-3 flex-1">
          {Array.from({ length: displayInnings }).map((_, idx) => {
            const inning = idx + 1;
            const runsKeyTop = `${inning}_true`;
            const displayRuns = inningRuns?.[runsKeyTop] ?? 0;
            const hasEntryBeenPlayed = inning <= currentInning;
            const showRuns = hasEntryBeenPlayed ? displayRuns : '';

            return (
              <div
                key={`away-inning-${inning}`}
                className={`${inningColWidth} text-center flex-shrink-0`}
              >
                <span className={`font-mono ${inningDataSize} text-[#C5A059] font-bold`}>
                  {showRuns}
                </span>
              </div>
            );
          })}
        </div>

        {/* Totals: R H E */}
        <div className="flex gap-0.5 sm:gap-2 md:gap-4 ml-1 sm:ml-2 md:ml-4 flex-shrink-0">
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${scoreSize} text-[#F7F5F0] font-bold`}>
              {awayScore}
            </span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${inningDataSize} text-[#F7F5F0] font-bold`}>
              {awayHits}
            </span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${inningDataSize} text-[#F7F5F0] font-bold`}>
              0
            </span>
          </div>
        </div>
      </div>

      {/* HOME TEAM ROW - ABAJO */}
      <div className="flex items-center px-2 sm:px-3 md:px-4 py-1 md:py-2 bg-[#0A0D0F] border-b border-[#C5A059]/10 min-w-max">
        {/* Team name */}
        <div className={`${teamNameWidth} truncate flex-shrink-0`}>
          <span className={`font-mono ${teamNameSize} text-[#F7F5F0] uppercase font-bold tracking-wider`}>
            {compact ? homeTeamName.substring(0, 4) : homeTeamName}
          </span>
        </div>

        {/* Inning runs */}
        <div className="flex gap-0.5 sm:gap-1 md:gap-3 flex-1">
          {Array.from({ length: displayInnings }).map((_, idx) => {
            const inning = idx + 1;
            const runsKeyBot = `${inning}_false`;
            const displayRuns = inningRuns?.[runsKeyBot] ?? 0;
            const hasEntryBeenPlayed = inning <= currentInning;
            const showRuns = hasEntryBeenPlayed ? displayRuns : '';

            return (
              <div
                key={`home-inning-${inning}`}
                className={`${inningColWidth} text-center flex-shrink-0`}
              >
                <span className={`font-mono ${inningDataSize} text-[#C5A059] font-bold`}>
                  {showRuns}
                </span>
              </div>
            );
          })}
        </div>

        {/* Totals: R H E */}
        <div className="flex gap-0.5 sm:gap-2 md:gap-4 ml-1 sm:ml-2 md:ml-4 flex-shrink-0">
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${scoreSize} text-[#F7F5F0] font-bold`}>
              {homeScore}
            </span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${inningDataSize} text-[#F7F5F0] font-bold`}>
              {homeHits}
            </span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${inningDataSize} text-[#F7F5F0] font-bold`}>
              0
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

Scoreboard.displayName = 'Scoreboard';
