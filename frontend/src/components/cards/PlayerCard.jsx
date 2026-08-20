import React from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../../utils/audioManager';

export const PlayerCard = ({ player, isSelected, onClick, role = "BATTER" }) => {
  const { t } = useTranslation();

  if (!player) return null;

  return (
    <div
      onClick={() => {
        soundFx.playCardSelect();
        if (onClick) onClick(player);
      }}
      className={`relative w-36 h-52 bg-[#0A0D0F] border-2 cursor-pointer transition-all duration-150 p-2 flex flex-col justify-between select-none ${
        isSelected
          ? 'border-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.5)] -translate-y-2'
          : 'border-[#2C3E35] hover:border-[#E6DFD3] hover:-translate-y-1'
      }`}
    >
      {/* Rol traducido */}
      <div className="flex justify-between items-center border-b border-[#2C3E35] pb-1">
        <span className="font-mono text-[9px] text-[#C5A059] uppercase tracking-wider">
          {role === "PITCHER" ? t('card.pitcher') : t('card.batter')}
        </span>
        <span className="font-sports text-lg text-[#F7F5F0] leading-none">
          {player.overall || 85}
        </span>
      </div>

      <div className="my-auto text-center py-2 bg-[#121619] border border-[#2C3E35]">
        <div className="font-sports text-4xl text-[#C5A059] leading-none">
          #{player.number || "00"}
        </div>
        <div className="font-mono text-[8px] text-[#E6DFD3] uppercase tracking-widest mt-1">
          {player.position || (role === "PITCHER" ? "RHP" : "OF")}
        </div>
      </div>

      {/* Atributos traducidos */}
      <div className="border-t border-[#2C3E35] pt-1">
        <div className="font-sports text-xl text-[#F7F5F0] truncate leading-none uppercase">
          {player.name || "Jugador"}
        </div>
        <div className="flex justify-between text-[8px] font-mono text-[#E6DFD3] mt-1">
          {role === "PITCHER" ? (
            <>
              <span>{t('card.velocity')}: {player.velocity || 95}</span>
              <span>{t('card.control')}: {player.control || 80}</span>
            </>
          ) : (
            <>
              <span>{t('card.power')}: {player.power || 78}</span>
              <span>{t('card.contact')}: {player.contact || 82}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};