import React from 'react';
import { GameStateWS, PlayerRole } from '../../types/stadium';

interface ScoreboardProps {
  gameState: GameStateWS;
  role: PlayerRole;
}

/**
 * Scoreboard — Marcador en tiempo real
 * ======================================
 * Muestra el inning, media entrada, marcador y conteo (B/S/O).
 * Recibe GameStateWS cuyo shape proviene del hook useStadiumSocket,
 * que a su vez mapea el payload PLAY_RESOLVED del backend.
 *
 * Campos usados de GameStateWS:
 *   currentInning  — Número de entrada (1-based)
 *   isTopInning    — true = Alta, false = Baja
 *   homeScore      — Carreras del equipo local
 *   awayScore      — Carreras del equipo visitante
 *   balls/strikes/outs — Conteo actual del at-bat
 */
export const Scoreboard: React.FC<ScoreboardProps> = ({ gameState, role }) => {
  const {
    currentInning = 1,
    isTopInning = true,
    homeScore = 0,
    awayScore = 0,
    balls = 0,
    strikes = 0,
    outs = 0,
  } = gameState || {};

  // Convertir número de inning a ordinal para display
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
          STADIUM MATCH
        </span>
      </div>

      {/* Columna Centro: Marcador */}
      <div className="text-center mx-auto">
        <div className="font-sports text-4xl tracking-widest text-[#F7F5F0]">
          LAD <strong className="text-[#C5A059]">{homeScore}</strong> -{' '}
          <strong className="text-[#F7F5F0]">{awayScore}</strong> NYY
        </div>
      </div>

      {/* Columna Derecha: Conteo B/S/O */}
      <div className="text-sm flex gap-4 text-[#E6DFD3] font-bold justify-end items-center">
        <span>B: <strong className="text-[#C5A059]">{balls}</strong></span>
        <span>S: <strong className="text-[#C5A059]">{strikes}</strong></span>
        <span>O: <strong className="text-[#C5A059]">{outs}</strong></span>
        <div className="flex gap-1 ml-2">
          <div className={`w-3 h-3 rotate-45 border ${outs >= 1 ? 'border-[#C5A059] bg-[#C5A059]' : 'border-[#2C3E35] bg-[#121619]'}`} />
          <div className={`w-3 h-3 rotate-45 border ${outs >= 2 ? 'border-[#C5A059] bg-[#C5A059]' : 'border-[#2C3E35] bg-[#121619]'}`} />
        </div>
      </div>
    </div>
  );
};
