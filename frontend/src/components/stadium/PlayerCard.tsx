import React from 'react';
import { motion } from 'framer-motion';
import { PlayerData, PlayerRole } from '../../types/stadium';

// ============ TYPE DEFINITIONS ============

interface PlayerCardProps {
  player: PlayerData | null;
  role: PlayerRole;
  disableEffects?: boolean;
  disablePulse?: boolean;
  responsive?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

interface TierConfig {
  tierLabel: string;
  accentColor: string;
  glowColor: string;
  shadowColor: string;
}

interface StatConfig {
  label: string;
  val: number;
}

/**
 * PlayerCard Component - Responsive & Tier-based design
 * 
 * Sizes:
 * - sm: Mobile (w-full, scales down)
 * - md: Tablet (w-48, balanced)
 * - lg: Desktop (w-56, full size)
 * 
 * Responsive scaling:
 * - Jersey: text-3xl → text-4xl → text-5xl
 * - Name: text-[8px] → text-[9px] → text-[10px]
 * - Stats: text-[6px] → text-[7px] → text-[8px]
 */
export const PlayerCard: React.FC<PlayerCardProps> = ({
  player,
  role,
  disableEffects = false,
  disablePulse = false,
  responsive = true,
  size = 'md',
}) => {
  const tierConfig = getTierConfig(player?.rarity);
  const roleStats = getRoleStatsConfig(role);

  // Responsive sizing
  const cardSizeClass = {
    sm: 'w-full sm:w-40 md:w-48',
    md: 'w-full sm:w-48 md:w-56',
    lg: 'w-full sm:w-56 md:w-64',
  }[size];

  const jerseySize = {
    sm: 'text-3xl sm:text-4xl md:text-5xl',
    md: 'text-4xl sm:text-5xl md:text-6xl',
    lg: 'text-5xl sm:text-6xl md:text-7xl',
  }[size];

  const statLabelSize = {
    sm: 'text-[6px] sm:text-[7px] md:text-[8px]',
    md: 'text-[8px] sm:text-[9px] md:text-[10px]',
    lg: 'text-[9px] sm:text-[10px] md:text-[11px]',
  }[size];

  const playerNameSize = {
    sm: 'text-[8px] sm:text-[9px] md:text-[10px]',
    md: 'text-[9px] sm:text-[10px] md:text-[11px]',
    lg: 'text-[10px] sm:text-[11px] md:text-[13px]',
  }[size];

  const teamNameSize = {
    sm: 'text-[6px] sm:text-[7px] md:text-[8px]',
    md: 'text-[7px] sm:text-[8px] md:text-[9px]',
    lg: 'text-[8px] sm:text-[9px] md:text-[10px]',
  }[size];

  const headerSize = {
    sm: 'text-[7px] sm:text-[8px] md:text-[9px]',
    md: 'text-[8px] sm:text-[9px] md:text-[10px]',
    lg: 'text-[9px] sm:text-[10px] md:text-[11px]',
  }[size];

  if (!player) {
    return (
      <div className={`${cardSizeClass} aspect-[3/4] z-10 bg-[#0A0D0F]/90 border p-2 sm:p-3 md:p-4 shadow-2xl flex flex-col items-center justify-center`}
        style={{ borderColor: tierConfig.accentColor }}>
        <span className={`font-mono ${headerSize} animate-pulse`} style={{ color: tierConfig.accentColor }}>
          LOADING...
        </span>
      </div>
    );
  }

  // Animation configuration
  const animationConfig = disableEffects
    ? {
      animate: {},
      whileHover: {},
      whileTap: {},
    }
    : {
      animate: disablePulse
        ? {}
        : {
          boxShadow: [
            `0 0 20px ${tierConfig.shadowColor}, inset 0 0 10px rgba(255, 255, 255, 0.05)`,
            `0 0 40px ${tierConfig.shadowColor}, inset 0 0 15px rgba(255, 255, 255, 0.1)`,
            `0 0 20px ${tierConfig.shadowColor}, inset 0 0 10px rgba(255, 255, 255, 0.05)`,
          ],
        },
      transition: disablePulse
        ? {}
        : {
          duration: 2.5,
          repeat: Infinity,
          ease: 'easeInOut',
        },
      whileHover: {
        scale: 1.08,
        y: -8,
        boxShadow: `0 0 60px ${tierConfig.shadowColor}, 0 0 60px ${tierConfig.glowColor}`,
        transition: { duration: 0.2 },
      },
      whileTap: { scale: 0.96 },
    };

  // Get player stats matching role config
  const displayStats = player?.stats?.length > 0
    ? player.stats.slice(0, 3)
    : roleStats.map((label) => ({ label, val: 0 }));

  return (
    <motion.div
      className={`${cardSizeClass} aspect-[3/4] relative z-10 bg-[#0A0D0F]/90 p-2 sm:p-3 md:p-4 backdrop-blur-sm rounded-xs cursor-pointer select-none flex flex-col`}
      style={{
        borderWidth: '2px',
        borderColor: tierConfig.accentColor,
        backgroundColor: '#0A0D0F',
        boxShadow: disableEffects
          ? `0 0 20px ${tierConfig.shadowColor}, inset 0 0 10px rgba(255, 255, 255, 0.05)`
          : undefined,
      }}
      animate={animationConfig.animate}
      transition={animationConfig.transition}
      whileHover={animationConfig.whileHover}
      whileTap={animationConfig.whileTap}
    >
      {/* HEADER: Tier + OVR - Responsive sizing */}
      <div className="flex justify-between items-center border-b pb-1 sm:pb-1.5 md:pb-2 mb-2 md:mb-3" style={{ borderColor: tierConfig.accentColor }}>
        <span className={`font-mono ${headerSize} font-bold tracking-wider uppercase`} style={{ color: tierConfig.accentColor }}>
          {tierConfig.tierLabel.substring(0, 3)}
        </span>
        <span className={`font-mono text-sm sm:text-base md:text-lg font-bold`} style={{ color: tierConfig.accentColor }}>
          {player?.overall ?? '--'}
        </span>
      </div>

      {/* JERSEY NUMBER - Responsive sizing with aspect ratio */}
      <div className="text-center py-3 sm:py-4 md:py-6 bg-[#121619] border mb-2 md:mb-3 flex-1 flex items-center justify-center" style={{ borderColor: `${tierConfig.accentColor}40` }}>
        <div className={`font-sports ${jerseySize} leading-none font-bold`} style={{ color: tierConfig.glowColor }}>
          #{player?.number || '0'}
        </div>
      </div>

      {/* PLAYER NAME - Responsive sizing */}
      <h4 className={`font-mono ${playerNameSize} text-[#F7F5F0] leading-tight mb-2 md:mb-3 truncate text-center uppercase font-bold tracking-wide`}>
        {player?.name || 'Loading...'}
      </h4>

      {/* STATS GRID - Responsive sizing */}
      <div className="grid grid-cols-3 gap-0.5 sm:gap-1 md:gap-1 mb-1 md:mb-2">
        {displayStats.map((stat) => (
          <div
            key={stat.label}
            className="flex flex-col items-center justify-center p-0.5 sm:p-1 md:p-1 rounded border"
            style={{
              borderColor: `${tierConfig.accentColor}60`,
              backgroundColor: `${tierConfig.accentColor}08`,
            }}
          >
            <span className={`font-mono ${statLabelSize} font-bold uppercase tracking-wider`} style={{ color: tierConfig.accentColor }}>
              {stat.label}
            </span>
            <span className={`font-mono text-xs sm:text-sm md:text-base font-bold mt-0.5`} style={{ color: tierConfig.glowColor }}>
              {stat.val}
            </span>
          </div>
        ))}
      </div>

      {/* FOOTER: Team Info - Responsive sizing */}
      <div className="border-t pt-1 md:pt-2 mt-auto" style={{ borderColor: tierConfig.accentColor }}>
        <div className="text-center">
          <div className={`text-[6px] sm:text-[7px] md:text-[8px] font-mono uppercase tracking-wider`} style={{ color: tierConfig.accentColor }}>
            ⚾ {player?.team || 'UNKNOWN'}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

PlayerCard.displayName = 'PlayerCard';

export default PlayerCard;

// ============ HELPER FUNCTIONS ============

/**
 * Get tier configuration based on player overall rating
 */
// Mapeo de colores por rareza (homologado con OnboardingScreen)
const RARITY_COLOR_CONFIG = {
  DIAMOND: {
    tierLabel: 'DIAMOND',
    accentColor: '#9966FF',
    glowColor: '#9966FF',
    shadowColor: 'rgba(153, 102, 255, 0.8)',
  },
  GOLD: {
    tierLabel: 'GOLD',
    accentColor: '#FFD700',
    glowColor: '#FFD700',
    shadowColor: 'rgba(255, 215, 0, 0.7)',
  },
  SILVER: {
    tierLabel: 'SILVER',
    accentColor: '#C0C0C0',
    glowColor: '#C0C0C0',
    shadowColor: 'rgba(192, 192, 192, 0.6)',
  },
  BRONZE: {
    tierLabel: 'BRONZE',
    accentColor: '#CD7F32',
    glowColor: '#CD7F32',
    shadowColor: 'rgba(205, 127, 50, 0.6)',
  },
  COMMON: {
    tierLabel: 'COMMON',
    accentColor: '#808080',
    glowColor: '#808080',
    shadowColor: 'rgba(128, 128, 128, 0.5)',
  },
};

/**
 * Get tier config based on rarity level
 * Homologated with OnboardingScreen colors
 */
function getTierConfig(rarity?: string): TierConfig {
  const rarityKey = (rarity ?? 'COMMON').toUpperCase();
  return RARITY_COLOR_CONFIG[rarityKey as keyof typeof RARITY_COLOR_CONFIG] || RARITY_COLOR_CONFIG.COMMON;
}

/**
 * Get role-specific stats configuration
 */
function getRoleStatsConfig(role: PlayerRole): StatConfig[] {
  switch (role) {
    case 'PITCHER':
      return [
        { label: 'VELO', val: 0 },
        { label: 'CTRL', val: 0 },
        { label: 'STAM', val: 0 },
      ];
    case 'BATTER':
      return [
        { label: 'CON', val: 0 },
        { label: 'POW', val: 0 },
        { label: 'SPD', val: 0 },
      ];
    default:
      return [
        { label: 'CON', val: 0 },
        { label: 'POW', val: 0 },
        { label: 'DEF', val: 0 },
      ];
  }
}