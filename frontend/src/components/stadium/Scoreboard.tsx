import React from 'react';
import { GameStateWS, PlayerRole } from '../../types/stadium';

interface ScoreboardProps {
  gameState: GameStateWS;
  role: PlayerRole;
  homeTeamName?: string;
  awayTeamName?: string;
  homeColor?: string;
  awayColor?: string;
}

/**
 * Scoreboard — Marcador en tiempo real dinámico
 */
export const Scoreboard: React.FC<ScoreboardProps> = ({
  gameState,
  role,
  homeTeamName = 'HOME',
  awayTeamName = 'CPU',
  homeColor = '#C5A059',
  awayColor = '#F7F5F0',
}) => {
  const {
    currentInning = 1,
    isTopInning = true,
    homeScore = 0,
    awayScore = 0,
    balls = 0,
    strikes = 0,
    outs = 0,
    runners = { b1: null, b2: null, b3: null },
  } = gameState || {};

  const inningOrdinals: Record<number, string> = {
    1: '1ST', 2: '2ND', 3: '3RD', 4: '4TH', 5: '5TH',
    6: '6TH', 7: '7TH', 8: '8TH', 9: '9TH',
  };
  const inningLabel = inningOrdinals[currentInning] ?? `${currentInning}TH`;
  const halfLabel = isTopInning ? 'TOP' : 'BOT';

  return (
    <div className="w-full max-w-6xl mx-auto bg-[#0A0D0F] border border-[#C5A059]/60 px-6 py-2.5 grid grid-cols-3 items-center shadow-2xl mb-3 font-mono">
      {/* Columna Izquierda: Inning & Rol */}
      <div className="flex flex-col justify-center items-start">
        <span className="text-sm text-[#C5A059] font-bold uppercase tracking-wider">
          {inningLabel} {halfLabel} • {role === 'PITCHER' ? 'DEFENSA' : 'ATAQUE'}
        </span>
        <span className="text-[10px] text-[#E6DFD3]/60 uppercase tracking-widest">
          {gameState?.lastEvent || 'PARTIDO EN VIVO'}
        </span>
      </div>

      {/* Columna Centro: Nombres y Marcador Dinámicos */}
      <div className="text-center mx-auto">
        <div className="font-sports text-4xl tracking-widest text-[#F7F5F0] flex items-center justify-center gap-3">
          <span style={{ color: homeColor }}>{homeTeamName}</span>
          <strong className="text-[#C5A059]">{homeScore}</strong>
          <span className="text-gray-500">-</span>
          <strong className="text-[#F7F5F0]">{awayScore}</strong>
          <span style={{ color: awayColor }}>{awayTeamName}</span>
        </div>
      </div>

      {/* Columna Derecha: Conteo B/S/O y Diamante de Corredores */}
      <div className="text-sm flex gap-4 text-[#E6DFD3] font-bold justify-end items-center">
        <span>B: <strong className="text-[#C5A059]">{balls}</strong></span>
        <span>S: <strong className="text-[#C5A059]">{strikes}</strong></span>
        <span>O: <strong className="text-[#C5A059]">{outs}</strong></span>

        {/* Diamante de bases */}
        <div className="relative w-7 h-7 flex items-center justify-center ml-2">
          {/* Segunda Base */}
          <div className={`absolute top-0 w-2.5 h-2.5 rotate-45 border transition-all ${runners?.b2 ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`} />
          {/* Tercera Base */}
          <div className={`absolute left-0 w-2.5 h-2.5 rotate-45 border transition-all ${runners?.b3 ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`} />
          {/* Primera Base */}
          <div className={`absolute right-0 w-2.5 h-2.5 rotate-45 border transition-all ${runners?.b1 ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`} />
        </div>
      </div>
    </div>
  );
};