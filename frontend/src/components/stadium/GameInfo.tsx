import React from 'react';
import { motion } from 'framer-motion';
import { PlayerRole } from '../../types/stadium';

interface GameInfoProps {
  balls: number;
  strikes: number;
  outs: number;
  currentInning: number;
  totalInnings: number;
  isTopInning: boolean;
  role: PlayerRole;
  runners: { b1: string | null; b2: string | null; b3: string | null };
}

/**
 * GameInfo — Panel compacto con B/S/O, Inning y Bases
 * Se muestra justo arriba del pitch zone
 */
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
    <div className="w-full bg-[#0A0D0F] border-2 border-[#C5A059]/40 rounded-xs px-4 py-2 flex justify-around items-center gap-6 mb-1 overflow-hidden">
      {/* B/S/O */}
      <div className="flex items-center gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-[#C5A059]">{balls}</div>
          <div className="text-[9px] text-[#E6DFD3]/70 font-mono">BOLAS</div>
        </div>
        <div className="w-px h-10 bg-[#C5A059]/20"></div>
        <div className="text-center">
          <div className="text-2xl font-bold text-[#C5A059]">{strikes}</div>
          <div className="text-[9px] text-[#E6DFD3]/70 font-mono">STRIKES</div>
        </div>
        <div className="w-px h-10 bg-[#C5A059]/20"></div>
        <div className="text-center">
          <div className="text-2xl font-bold text-[#C5A059]">{outs}</div>
          <div className="text-[9px] text-[#E6DFD3]/70 font-mono">OUTS</div>
        </div>
      </div>

      {/* Separador */}
      <div className="h-12 w-px bg-[#C5A059]/20"></div>

      {/* Inning + Half */}
      <div className="flex flex-col items-center gap-1">
        <div className="text-xl font-bold text-[#C5A059]">{currentInning}/{totalInnings}</div>
        <div className="text-sm font-bold" style={{ color: isTopInning ? '#C5A059' : '#F7F5F0' }}>
          {isTopInning ? '▼ TOP' : '▲ BOT'}
        </div>
        <div className="text-[8px] text-[#C5A059]/60 uppercase font-bold">
          {role === 'PITCHER' ? 'DEFENSA' : 'ATAQUE'}
        </div>
      </div>

      {/* Separador */}
      <div className="h-12 w-px bg-[#C5A059]/20"></div>

      {/* Bases - Diamante */}
      <div className="flex flex-col items-center gap-2">
        <div className="text-xs text-[#C5A059] font-bold uppercase">BASES</div>
        <div className="relative w-12 h-12 flex items-center justify-center">
          {/* Segunda Base (top) */}
          <motion.div
            className={`absolute top-0 w-3 h-3 rotate-45 border-2 rounded-sm transition-all ${
              runners?.b2 ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'
            }`}
            animate={runners?.b2 ? { scale: [1, 1.15, 1] } : {}}
            transition={{ duration: 0.4 }}
          />
          {/* Tercera Base (left) */}
          <motion.div
            className={`absolute left-0 w-3 h-3 rotate-45 border-2 rounded-sm transition-all ${
              runners?.b3 ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'
            }`}
            animate={runners?.b3 ? { scale: [1, 1.15, 1] } : {}}
            transition={{ duration: 0.4 }}
          />
          {/* Primera Base (right) */}
          <motion.div
            className={`absolute right-0 w-3 h-3 rotate-45 border-2 rounded-sm transition-all ${
              runners?.b1 ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'
            }`}
            animate={runners?.b1 ? { scale: [1, 1.15, 1] } : {}}
            transition={{ duration: 0.4 }}
          />
          {/* Home (center) */}
          <div className="absolute w-2.5 h-2.5 rotate-45 border-2 border-[#C5A059]/30 bg-[#0A0D0F]" />
        </div>
      </div>
    </div>
  );
};
