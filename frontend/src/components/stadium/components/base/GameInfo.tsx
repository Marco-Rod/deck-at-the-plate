/**
 * GameInfo - Horizontal game count display (Balls, Strikes, Outs, Inning, Bases)
 * 
 * Diseño tipo scoreboard profesional:
 * - Layout horizontal compacto
 * - B/S/O en números grandes
 * - Inning en el centro (1/3 TOP 1ST)
 * - Bases como diamantes en la derecha
 * 
 * @component
 * @example
 * <GameInfo 
 *   balls={0}
 *   strikes={2}
 *   outs={1}
 *   currentInning={1}
 *   totalInnings={9}
 *   isTopInning={true}
 *   runners={{ b1: null, b2: null, b3: null }}
 * />
 */

import React from 'react';
import type { GameInfoProps } from '../../types/stadium.types';

export const GameInfo: React.FC<GameInfoProps> = ({
  balls,
  strikes,
  outs,
  currentInning,
  totalInnings,
  isTopInning,
  role,
  runners,
}) => {
  return (
    <div className="w-full bg-[#0A0D0F]/95 border border-[#C5A059]/40 rounded-sm p-3">
      <div className="flex items-center justify-between gap-8 h-20">
        
        {/* LEFT: BALLS / STRIKES / OUTS */}
        <div className="flex gap-8">
          {/* Balls */}
          <div className="text-center min-w-fit">
            <div className="font-sports text-3xl text-[#F7F5F0] font-bold leading-tight">
              {balls}
            </div>
            <div className="font-mono text-[8px] text-[#C5A059] uppercase font-bold tracking-wider mt-1">
              B
            </div>
          </div>

          {/* Strikes */}
          <div className="text-center min-w-fit">
            <div className="font-sports text-3xl text-[#F7F5F0] font-bold leading-tight">
              {strikes}
            </div>
            <div className="font-mono text-[8px] text-[#C5A059] uppercase font-bold tracking-wider mt-1">
              S
            </div>
          </div>

          {/* Outs */}
          <div className="text-center min-w-fit">
            <div className="font-sports text-3xl text-[#F7F5F0] font-bold leading-tight">
              {outs}
            </div>
            <div className="font-mono text-[8px] text-[#C5A059] uppercase font-bold tracking-wider mt-1">
              O
            </div>
          </div>
        </div>

        {/* CENTER: INNING INFO - FLEX-1 TO CENTER */}
        <div className="flex-1 text-center">
          <div className="font-mono text-[12px] text-[#E6DFD3] uppercase font-bold tracking-wider">
            {currentInning}/{totalInnings}
          </div>
          <div className="font-mono text-[11px] text-[#C5A059] uppercase font-bold mt-1">
            {isTopInning ? 'TOP' : 'BOT'}
          </div>
        </div>

        {/* RIGHT: BASES DIAMOND (MLB Style) */}
        <div className="flex items-center justify-end ml-auto">
          {/* MLB Diamond Layout */}
          <div className="flex flex-col items-center gap-1">
            {/* Top base (2B) */}
            <div className="flex justify-center">
              <div className={`w-5 h-5 rotate-45 border-2 transition-colors ${
                runners.b2 
                  ? 'bg-[#C5A059]/40 border-[#C5A059]' 
                  : 'bg-transparent border-[#C5A059]/40'
              }`} />
            </div>

            {/* Middle row: 3B (left) and 1B (right) */}
            <div className="flex gap-3 items-center justify-center">
              {/* Base 3 (left) */}
              <div className={`w-5 h-5 rotate-45 border-2 transition-colors ${
                runners.b3 
                  ? 'bg-[#C5A059]/40 border-[#C5A059]' 
                  : 'bg-transparent border-[#C5A059]/40'
              }`} />

              {/* Home plate (center) - filled indicator */}
              <div className="w-3 h-3 bg-[#C5A059]/20 border border-[#C5A059]/60 rounded-sm" />

              {/* Base 1 (right) */}
              <div className={`w-5 h-5 rotate-45 border-2 transition-colors ${
                runners.b1 
                  ? 'bg-[#C5A059]/40 border-[#C5A059]' 
                  : 'bg-transparent border-[#C5A059]/40'
              }`} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

GameInfo.displayName = 'GameInfo';
