import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../../utils/audioManager';

// Mapeo de colores por rareza
const RARITY_COLORS = {
  DIAMOND: {
    border: '#9966FF',
    shadow: 'rgba(153, 102, 255, 0.8)',
    glow: '#9966FF',
  },
  GOLD: {
    border: '#FFD700',
    shadow: 'rgba(255, 215, 0, 0.7)',
    glow: '#FFD700',
  },
  SILVER: {
    border: '#C0C0C0',
    shadow: 'rgba(192, 192, 192, 0.6)',
    glow: '#C0C0C0',
  },
  BRONZE: {
    border: '#CD7F32',
    shadow: 'rgba(205, 127, 50, 0.6)',
    glow: '#CD7F32',
  },
  COMMON: {
    border: '#808080',
    shadow: 'rgba(128, 128, 128, 0.5)',
    glow: '#808080',
  },
};

const getRarityColor = (rarity) => {
  const key = (rarity || 'COMMON').toUpperCase();
  return RARITY_COLORS[key] || RARITY_COLORS.COMMON;
};

const getPulseIntensity = (rarity) => {
  const key = (rarity || 'COMMON').toUpperCase();
  const intensities = {
    DIAMOND: '0px 0px 20px, 0px 0px 40px',
    GOLD: '0px 0px 15px, 0px 0px 30px',
    SILVER: '0px 0px 12px, 0px 0px 25px',
    BRONZE: '0px 0px 10px, 0px 0px 20px',
    COMMON: '0px 0px 8px, 0px 0px 15px',
  };
  return intensities[key] || intensities.COMMON;
};

export const PlayerCard = ({ player, cardData, isSelected, onClick, role = "BATTER" }) => {
  const { t } = useTranslation();
  const [isFlipped, setIsFlipped] = useState(true); // Inicia boca abajo

  if (!player && !cardData) return null;

  const card = player || cardData;
  const rarity = card.rarity || 'COMMON';
  const rarityConfig = getRarityColor(rarity);
  const pulseIntensity = getPulseIntensity(rarity);

  const handleCardClick = () => {
    if (soundFx?.playCardReveal) soundFx.playCardReveal();
    setIsFlipped(!isFlipped);
    if (onClick) onClick(card);
  };

  // Efecto de pulso CSS inline para máxima compatibilidad
  const pulseAnimation = `
    @keyframes rarePulse_${rarity} {
      0%, 100% {
        box-shadow: 0 0 5px ${rarityConfig.shadow}, 
                    inset 0 0 10px rgba(255, 255, 255, 0);
      }
      50% {
        box-shadow: 0 0 25px ${rarityConfig.shadow}, 
                    inset 0 0 15px rgba(255, 255, 255, 0.1);
      }
    }
  `;

  return (
    <>
      <style>{pulseAnimation}</style>
      <div
        onClick={handleCardClick}
        data-is-card="true"
        data-card-flipped={isFlipped}
        className={`relative w-40 h-56 cursor-pointer transition-all duration-300 p-2 flex flex-col justify-between select-none transform-gpu`}
        style={{
          borderWidth: '3px',
          borderColor: rarityConfig.border,
          backgroundColor: '#0A0D0F',
          boxShadow: `0 0 20px ${rarityConfig.shadow}, inset 0 0 10px rgba(255, 255, 255, 0.05)`,
          animation: `rarePulse_${rarity} 2.5s ease-in-out infinite`,
          transformStyle: 'preserve-3d',
          transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
          transition: 'transform 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55), box-shadow 0.3s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = `0 0 40px ${rarityConfig.shadow}, inset 0 0 15px rgba(255, 255, 255, 0.15), 0 0 60px ${rarityConfig.glow}`;
          if (rarity === 'DIAMOND') {
            e.currentTarget.style.transform = isFlipped ? 'rotateY(180deg) scale(1.08)' : 'rotateY(0deg) scale(1.08)';
          } else if (rarity === 'GOLD') {
            e.currentTarget.style.transform = isFlipped ? 'rotateY(180deg) scale(1.06)' : 'rotateY(0deg) scale(1.06)';
          } else {
            e.currentTarget.style.transform = isFlipped ? 'rotateY(180deg) scale(1.04)' : 'rotateY(0deg) scale(1.04)';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = `0 0 20px ${rarityConfig.shadow}, inset 0 0 10px rgba(255, 255, 255, 0.05)`;
          e.currentTarget.style.transform = isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)';
        }}
      >
        {/* FRENTE DE LA CARTA */}
        <div
          style={{
            backfaceVisibility: 'hidden',
            WebkitBackfaceVisibility: 'hidden',
          }}
        >
          {/* Rol traducido */}
          <div className="flex justify-between items-center border-b pb-1" style={{ borderColor: rarityConfig.border }}>
            <span className="font-mono text-[9px] uppercase tracking-wider" style={{ color: rarityConfig.border }}>
              {role === "PITCHER" ? t('card.pitcher') : t('card.batter')}
            </span>
            <span className="font-sports text-lg text-[#F7F5F0] leading-none">
              {card.overall || 85}
            </span>
          </div>

          <div className="my-auto text-center py-2 bg-[#121619] border" style={{ borderColor: `${rarityConfig.border}40` }}>
            <div className="font-sports text-4xl leading-none" style={{ color: rarityConfig.glow }}>
              #{card.number || "00"}
            </div>
            <div className="font-mono text-[8px] text-[#E6DFD3] uppercase tracking-widest mt-1">
              {card.position || (role === "PITCHER" ? "RHP" : "OF")}
            </div>
          </div>

          {/* Atributos traducidos */}
          <div className="border-t pt-1" style={{ borderColor: rarityConfig.border }}>
            <div className="font-sports text-xl text-[#F7F5F0] truncate leading-none uppercase">
              {card.name || "Jugador"}
            </div>
            <div className="flex justify-between text-[8px] font-mono text-[#E6DFD3] mt-1 mb-1">
              {role === "PITCHER" ? (
                <>
                  <span>{t('card.velocity')}: {card.velocity || 95}</span>
                  <span>{t('card.control')}: {card.control || 80}</span>
                </>
              ) : (
                <>
                  <span>{t('card.power')}: {card.power || 78}</span>
                  <span>{t('card.contact')}: {card.contact || 82}</span>
                </>
              )}
            </div>
            {/* Equipo */}
            <div className="text-[8px] font-mono tracking-widest uppercase text-[#C5A059] border-t pt-1" style={{ borderColor: `${rarityConfig.border}40` }}>
              {card.team_id || card.teamId || "UNKNOWN"}
            </div>
          </div>

          {/* Indicador de Rareza */}
          <div
            className="absolute top-2 right-2 text-xs font-bold px-2 py-1 rounded-full uppercase"
            style={{
              backgroundColor: `${rarityConfig.border}20`,
              color: rarityConfig.border,
              textShadow: `0 0 8px ${rarityConfig.glow}`,
            }}
          >
            {rarity}
          </div>
        </div>

        {/* REVERSO DE LA CARTA (Flip) */}
        <div
          style={{
            backfaceVisibility: 'hidden',
            WebkitBackfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            padding: '0.5rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            backgroundColor: '#0A0D0F',
            borderRadius: '0.25rem',
          }}
        >
          <div className="text-center space-y-3">
            <div className="text-6xl animate-spin" style={{ animationDuration: '2s' }}>
              ⚾
            </div>
            <div className="font-sports text-lg uppercase" style={{ color: rarityConfig.glow }}>
              {rarity}
            </div>
            <div className="font-mono text-[10px] text-[#E6DFD3]">
              PRESIONA PARA REVELAR
            </div>
          </div>
        </div>
      </div>
    </>
  );
};