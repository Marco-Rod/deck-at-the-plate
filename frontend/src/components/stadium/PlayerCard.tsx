import React from 'react';
import { PlayerData, PlayerRole } from '../../types/stadium';

interface PlayerCardProps {
  player: PlayerData | null;
  role: PlayerRole;
}

// Fallback en SVG Data URI para evitar peticiones HTTP externas
const DEFAULT_AVATAR = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 24 24' fill='%23C5A059'><path d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z'/></svg>";

export const PlayerCard: React.FC<PlayerCardProps> = ({ player, role }) => {
  if (!player) {
    return (
      <div className="z-10 bg-[#0A0D0F]/90 border border-[#C5A059] p-3 w-60 shadow-2xl flex flex-col items-center justify-center min-h-[300px]">
        <span className="font-mono text-xs text-[#C5A059] animate-pulse">
          CARGANDO {role === 'PITCHER' ? 'LANZADOR' : 'BATEADOR'}...
        </span>
      </div>
    );
  }

  return (
    <div className="z-10 bg-[#0A0D0F]/90 border border-[#C5A059] p-3 w-60 shadow-2xl backdrop-blur-sm">
      <div className="flex justify-between items-center border-b border-[#2C3E35] pb-1 mb-2">
        <span className="font-mono text-[10px] text-[#C5A059] font-bold">
          {role === 'PITCHER' ? 'LANZADOR' : 'BATEADOR'}
        </span>
        <span className="font-sports text-xl text-[#F7F5F0]">
          {player?.overall ?? '--'}
        </span>
      </div>

      <div className="relative h-44 w-full bg-[#121619] border border-[#2C3E35] overflow-hidden mb-2 flex items-center justify-center">
        <img
          src={player?.photo || DEFAULT_AVATAR}
          alt={player?.name || 'Jugador'}
          onError={(e) => {
            // Evitamos el bucle infinito limpiando el handler
            const target = e.currentTarget;
            target.onerror = null; 
            target.src = DEFAULT_AVATAR;
          }}
          className="w-full h-full object-cover object-top"
        />
        <span className="absolute bottom-1 left-2 font-sports text-2xl text-[#C5A059] drop-shadow-md">
          #{player?.number || '0'}
        </span>
        <span className="absolute bottom-1 right-2 font-mono text-[10px] text-[#E6DFD3]">
          {player?.position || '--'}
        </span>
      </div>

      <h4 className="font-sports text-xl text-[#F7F5F0] leading-none mb-1 truncate">
        {player?.name || 'Cargando...'}
      </h4>

      <div className="space-y-1.5 font-mono text-[9px] mt-2">
        <span className="text-[#C5A059] font-bold block mb-1">ESTADÍSTICAS</span>
        {player?.stats?.map((s) => (
          <div key={s.label} className="flex items-center justify-between gap-2">
            <span className="w-6 text-[#E6DFD3]">{s.label}</span>
            <div className="flex-1 h-1.5 bg-[#121619] border border-[#2C3E35]">
              <div
                className="h-full bg-[#C5A059]"
                style={{ width: `${Math.min(s.val, 100)}%` }}
              />
            </div>
            <span className="w-5 text-right">{s.val}</span>
          </div>
        ))}
      </div>
    </div>
  );
};