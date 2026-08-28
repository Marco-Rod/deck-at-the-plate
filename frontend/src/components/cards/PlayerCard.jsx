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

// Función auxiliar para obtener clases por tamaño
const getSizeClasses = (size) => {
  const sizeMap = {
    xs: 'w-24 h-32 text-xs',
    sm: 'w-32 h-44 text-sm',
    md: 'w-40 h-56 text-base',
    lg: 'w-48 h-64 text-lg',
  };
  return sizeMap[size] || sizeMap.md;
};

/**
 * PlayerCard - Componente de visualización flexible de cartas de jugador
 * 
 * @param {Object} props
 * @param {Object} props.card - Datos de la carta (puede ser player o cardData)
 * @param {Object} props.player - Alias para card
 * @param {Object} props.cardData - Alias para card
 * @param {string} props.mode - Modo de visualización: "full" (3D flip), "compact" (lista), "grid" (thumbnail)
 * @param {string} props.size - Tamaño: "xs", "sm", "md" (default), "lg"
 * @param {boolean} props.isSelected - Si está seleccionada
 * @param {Function} props.onClick - Callback al hacer click
 * @param {string} props.role - Rol: "BATTER" (default) o "PITCHER"
 */
export const PlayerCard = ({ 
  player, 
  cardData, 
  card: directCard,
  isSelected = false,
  onClick,
  role = "BATTER",
  mode = "full",
  size = "md"
}) => {
  const { t } = useTranslation();
  const [isFlipped, setIsFlipped] = useState(mode === "full");

  if (!player && !cardData && !directCard) return null;

  const card = directCard || player || cardData;
  const rarity = card.rarity || 'COMMON';
  const rarityConfig = getRarityColor(rarity);
  const pulseIntensity = getPulseIntensity(rarity);
  const sizeClasses = getSizeClasses(size);

  const handleCardClick = () => {
    if (mode === "full") {
      if (soundFx?.playCardReveal) soundFx.playCardReveal();
      setIsFlipped(!isFlipped);
    } else if (mode === "compact" || mode === "grid") {
      if (soundFx?.playCardSelect) soundFx.playCardSelect();
    }
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
      
      {/* MODO FULL - 3D con Flip animado (revelar pack) */}
      {mode === "full" && (
        <div
          onClick={handleCardClick}
          data-is-card="true"
          data-card-flipped={isFlipped}
          className={`relative ${sizeClasses} cursor-pointer transition-all duration-300 p-2 flex flex-col justify-between select-none transform-gpu`}
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
              
              {/* Equipo - más visible */}
              <div 
                className="text-[9px] font-mono tracking-wider uppercase font-bold border-t pt-1 mt-1" 
                style={{ borderColor: rarityConfig.border, color: rarityConfig.border }}
              >
                ⚾ {card.team_id || card.teamId || "UNKNOWN"}
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
      )}

      {/* MODO COMPACT - Para listas y candidatos */}
      {mode === "compact" && (
        <div
          onClick={handleCardClick}
          className={`p-2 border transition-all cursor-pointer flex justify-between items-center rounded ${
            isSelected
              ? 'border-[#C5A059] bg-[#1A3323]'
              : 'border-[#2C3E35] bg-[#121619] hover:border-gray-400'
          }`}
          style={{
            borderColor: isSelected ? rarityConfig.border : undefined,
            backgroundColor: isSelected ? `${rarityConfig.shadow}20` : undefined,
          }}
        >
          <div className="overflow-hidden mr-2 flex-1">
            <div className="font-sports text-base text-white uppercase leading-tight truncate flex items-center gap-1">
              <span>{card.name}</span>
              <span 
                className="text-[8px] px-1 rounded font-bold"
                style={{
                  backgroundColor: `${rarityConfig.border}30`,
                  color: rarityConfig.border,
                }}
              >
                {rarity}
              </span>
            </div>
            <span className="text-[9px] text-gray-400 font-mono block">
              {card.position} • {card.team_id} • OVR {card.overall}
            </span>
          </div>
          <div className="text-right shrink-0">
            <span className="font-sports text-lg" style={{ color: rarityConfig.border }}>
              {card.overall}
            </span>
            {isSelected && (
              <span className="text-[8px] text-green-400 uppercase font-bold font-mono block">ASIGNADO</span>
            )}
          </div>
        </div>
      )}

      {/* MODO GRID - Thumbnails para galerías */}
      {mode === "grid" && (
        <div
          onClick={handleCardClick}
          className={`relative rounded overflow-hidden transition-all cursor-pointer transform-gpu ${sizeClasses} ${
            isSelected ? 'ring-2 scale-105' : 'hover:scale-105'
          }`}
          style={{
            borderWidth: '2px',
            borderColor: rarityConfig.border,
            backgroundColor: '#0A0D0F',
            boxShadow: `0 0 15px ${rarityConfig.shadow}`,
            ringColor: isSelected ? rarityConfig.border : undefined,
          }}
        >
          {/* Card Image / Placeholder */}
          <div className="w-full h-full bg-gradient-to-b from-[#1A3323] to-[#0A0D0F] flex flex-col items-center justify-center p-1">
            {/* Jersey Number */}
            <div 
              className="font-sports text-4xl font-bold"
              style={{ color: rarityConfig.glow }}
            >
              #{card.number || "00"}
            </div>

            {/* Name */}
            <div className="font-sports text-xs text-white uppercase truncate text-center mt-1 px-1">
              {card.name}
            </div>

            {/* Position & Overall */}
            <div className="text-[10px] text-gray-400 font-mono mt-1 text-center">
              <div>{card.position}</div>
              <div style={{ color: rarityConfig.border }} className="font-bold">
                {card.overall} OVR
              </div>
            </div>

            {/* Rarity Badge */}
            <div
              className="absolute top-1 right-1 text-[10px] font-bold px-1 py-0.5 rounded"
              style={{
                backgroundColor: `${rarityConfig.border}40`,
                color: rarityConfig.border,
              }}
            >
              {rarity.charAt(0)}
            </div>
          </div>
        </div>
      )}
    </>
  );
};