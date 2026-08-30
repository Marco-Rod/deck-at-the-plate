/**
 * GameHeader - Improved 2-line header for stadium gameplay
 * 
 * Propuesta 1 Improvement: 2-line layout with larger title
 * - Line 1: Title (text-4xl) + Lobby button (top-right)
 * - Line 2: Connection status (text-[9px], small)
 * 
 * @component
 * @example
 * <GameHeader teamName="AXOLOTES" isConnected={true} onBack={() => navigate('/')} />
 */

import React from 'react';
import type { GameHeaderProps } from '../../types/stadium.types';
import { COLORS, TYPOGRAPHY } from '../../constants/stadium.constants';

export const GameHeader: React.FC<GameHeaderProps> = ({
  teamName = 'CAMPO DE JUEGO',
  isConnected = false,
  onBack,
}) => {
  const connectionStatusClass = isConnected 
    ? 'text-emerald-400' 
    : 'text-red-400';
  
  const connectionText = isConnected 
    ? '● CONECTADO EN VIVO' 
    : '○ DESCONECTADO';

  const connectionIndicator = isConnected ? '●' : '○';

  return (
    <header className="w-full border-b-2 border-[#C5A059]/40 pb-4 mb-3 z-30">
      {/* LINE 1: Title + Lobby Button */}
      <div className="flex justify-between items-start mb-2">
        <h2 className="font-sports text-4xl text-[#F7F5F0] uppercase tracking-wider leading-none">
          {teamName}
        </h2>
        
        <button
          type="button"
          onClick={onBack}
          className="bg-[#0A0D0F] border border-[#C5A059] px-4 py-2 font-mono text-xs text-[#C5A059] font-bold cursor-pointer hover:bg-[#1A3323] transition-colors duration-200"
          aria-label="Return to lobby"
        >
          ⚙️ LOBBY
        </button>
      </div>

      {/* LINE 2: Connection Status */}
      <span className={`font-mono text-[9px] ${connectionStatusClass} flex items-center gap-1.5`}>
        <span>{connectionIndicator}</span>
        <span>{connectionText}</span>
      </span>
    </header>
  );
};

GameHeader.displayName = 'GameHeader';
