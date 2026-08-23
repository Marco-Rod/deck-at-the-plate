import React from 'react';
import { PlayerData, PlayerRole } from '../../types/stadium';

interface PlayerCardProps {
  player: PlayerData;
  role: PlayerRole;
  isMainUser?: boolean;
}

export const PlayerCard: React.FC<PlayerCardProps> = ({
  player,
  role,
  isMainUser = false,
}) => {
  return (
    <div className="z-10 bg-[#0A0D0F]/90 border border-[#C5A059] p-3 w-60 shadow-2xl backdrop-blur-sm">
      <div className="flex justify-between items-center border-b border-[#2C3E35] pb-1 mb-2">
        <span className="font-mono text-[10px] text-[#C5A059] font-bold uppercase">
          {role === 'PITCHER' ? 'PÍCHER' : 'BATEADOR'}
        </span>
        <span className="font-sports text-xl text-[#F7F5F0]">
          {player.overall}
        </span>
      </div>

      <div className="relative h-44 w-full bg-[#121619] border border-[#2C3E35] overflow-hidden mb-2">
        <img
          src={player.photo}
          alt={player.name}
          className="w-full h-full object-cover object-top"
        />
        <span className="absolute bottom-1 left-2 font-sports text-2xl text-[#C5A059] drop-shadow-md">
          #{player.number}
        </span>
        <span className="absolute bottom-1 right-2 font-mono text-[10px] text-[#E6DFD3]">
          {player.position}
        </span>
      </div>

      <h4 className="font-sports text-xl text-[#F7F5F0] leading-none mb-1">
        {player.name}
      </h4>
      <div className="font-mono text-[10px] text-[#E6DFD3] flex gap-3 mb-3 border-b border-[#2C3E35] pb-2">
        {player.stats.slice(0, 2).map((s) => (
          <span key={s.label}>
            {s.label}: {s.val}
          </span>
        ))}
      </div>

      {/* Barras de Atributos */}
      <div className="space-y-1.5 font-mono text-[9px]">
        <span className="text-[#C5A059] font-bold block mb-1">
          ESTADÍSTICAS
        </span>
        {player.stats.map((s) => (
          <div
            key={s.label}
            className="flex items-center justify-between gap-2"
          >
            <span className="w-6 text-[#E6DFD3]">{s.label}</span>
            <div className="flex-1 h-1.5 bg-[#121619] border border-[#2C3E35]">
              <div
                className="h-full bg-[#C5A059]"
                style={{ width: `${s.val}%` }}
              />
            </div>
            <span className="w-5 text-right">{s.val}</span>
          </div>
        ))}
      </div>
    </div>
  );
};