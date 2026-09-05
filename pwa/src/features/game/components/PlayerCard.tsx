import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import type { PlayerGameData, PlayerRole } from '@/shared/api/types'

interface PlayerCardProps {
  player: PlayerGameData | null
  role: PlayerRole
  disableEffects?: boolean
  disablePulse?: boolean
  size?: 'sm' | 'md' | 'lg'
  fatigueLevel?: number
  onClickPitcher?: () => void
}

interface TierConfig {
  tierLabel: string
  accentColor: string
  glowColor: string
  shadowColor: string
}

const RARITY_COLOR_CONFIG: Record<string, TierConfig> = {
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
}

const ANON_TIER: TierConfig = {
  tierLabel: 'COMMON',
  accentColor: '#808080',
  glowColor: '#808080',
  shadowColor: 'rgba(128, 128, 128, 0.5)',
}

const getTierConfig = (rarity?: string): TierConfig => {
  const rarityKey = (rarity ?? 'COMMON').toUpperCase()
  return RARITY_COLOR_CONFIG[rarityKey] ?? ANON_TIER
}

const getRoleStatsConfig = (role: PlayerRole): Array<{ label: string; val: number }> => {
  switch (role) {
    case 'PITCHER':
      return [
        { label: 'VELO', val: 0 },
        { label: 'CTRL', val: 0 },
        { label: 'STAM', val: 0 },
      ]
    case 'BATTER':
      return [
        { label: 'CON', val: 0 },
        { label: 'POW', val: 0 },
        { label: 'SPD', val: 0 },
      ]
    default:
      return [
        { label: 'CON', val: 0 },
        { label: 'POW', val: 0 },
        { label: 'DEF', val: 0 },
      ]
  }
}

export function PlayerCard({
  player,
  role,
  disableEffects = false,
  disablePulse = false,
  size = 'md',
  fatigueLevel = 0,
  onClickPitcher,
}: PlayerCardProps) {
  const { t } = useTranslation()
  const tierConfig = getTierConfig(player?.rarity)
  const roleStats = getRoleStatsConfig(role)

  const cardSizeClass = {
    sm: 'w-full sm:w-40 md:w-48',
    md: 'w-full sm:w-48 md:w-56',
    lg: 'w-full sm:w-56 md:w-64',
  }[size]

  const jerseySize = {
    sm: 'text-3xl sm:text-4xl md:text-5xl',
    md: 'text-4xl sm:text-5xl md:text-6xl',
    lg: 'text-5xl sm:text-6xl md:text-7xl',
  }[size]

  const statLabelSize = {
    sm: 'text-[6px] sm:text-[7px] md:text-[8px]',
    md: 'text-[8px] sm:text-[9px] md:text-[10px]',
    lg: 'text-[9px] sm:text-[10px] md:text-[11px]',
  }[size]

  const playerNameSize = {
    sm: 'text-[8px] sm:text-[9px] md:text-[10px]',
    md: 'text-[9px] sm:text-[10px] md:text-[11px]',
    lg: 'text-[10px] sm:text-[11px] md:text-[13px]',
  }[size]

  const headerSize = {
    sm: 'text-[7px] sm:text-[8px] md:text-[9px]',
    md: 'text-[8px] sm:text-[9px] md:text-[10px]',
    lg: 'text-[9px] sm:text-[10px] md:text-[11px]',
  }[size]

  if (!player) {
    return (
      <div
        className={`${cardSizeClass} z-10 flex aspect-[3/4] flex-col items-center justify-center border bg-koshien-dark/90 p-2 shadow-2xl sm:p-3 md:p-4`}
        style={{ borderColor: tierConfig.accentColor }}
      >
        <span
          className={`font-vintage ${headerSize} animate-pulse`}
          style={{ color: tierConfig.accentColor }}
        >
          {t('common.loading')}
        </span>
      </div>
    )
  }

  const isPulsing = !disableEffects && !disablePulse
  const vibrateIntensity = (fatigueLevel / 100) * 3
  const vibrationDuration = Math.max(0.2, 1 - fatigueLevel / 100)
  const shouldVibrate = role === 'PITCHER' && fatigueLevel > 0
  const isInteractive = role === 'PITCHER' && Boolean(onClickPitcher)
  const whileHover = disableEffects
    ? {}
    : {
        scale: 1.08 as const,
        y: -8 as const,
        boxShadow: `0 0 60px ${tierConfig.shadowColor}, 0 0 60px ${tierConfig.glowColor}`,
        transition: { duration: 0.2 },
      }
  const whileTap = disableEffects ? {} : { scale: 0.96 as const }

  const displayStats =
    player.stats && player.stats.length > 0
      ? player.stats.slice(0, 3)
      : roleStats.map((stat) => ({ label: stat.label, val: 0 }))

  return (
    <motion.div
      key={player.id}
      role={isInteractive ? 'button' : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      aria-label={isInteractive ? t('game.change_pitcher_title') : undefined}
      onKeyDown={isInteractive ? (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onClickPitcher?.()
        }
      } : undefined}
      className={`${cardSizeClass} relative z-10 flex aspect-[3/4] select-none flex-col rounded-xs bg-koshien-dark/90 p-2 backdrop-blur-sm sm:p-3 md:p-4 ${
        isInteractive ? 'cursor-pointer hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold' : ''
      }`}
      style={{
        borderWidth: '2px',
        borderColor: tierConfig.accentColor,
        backgroundColor: '#121619',
        boxShadow: disableEffects
          ? `0 0 20px ${tierConfig.shadowColor}, inset 0 0 10px rgba(255, 255, 255, 0.05)`
          : undefined,
      }}
      animate={{
        ...(isPulsing
          ? {
              boxShadow: [
                `0 0 20px ${tierConfig.shadowColor}, inset 0 0 10px rgba(255, 255, 255, 0.05)`,
                `0 0 40px ${tierConfig.shadowColor}, inset 0 0 15px rgba(255, 255, 255, 0.1)`,
                `0 0 20px ${tierConfig.shadowColor}, inset 0 0 10px rgba(255, 255, 255, 0.05)`,
              ],
            }
          : {}),
        ...(shouldVibrate && {
          x: [0, vibrateIntensity, -vibrateIntensity, vibrateIntensity, 0],
        }),
      }}
      transition={{
        ...(isPulsing
          ? { duration: 2.5, repeat: Infinity, ease: 'easeInOut' as const }
          : {}),
        ...(shouldVibrate && {
          x: { duration: vibrationDuration, repeat: Infinity, ease: 'easeInOut' as const },
        }),
      }}
      whileHover={whileHover}
      whileTap={whileTap}
      onClick={() => {
        if (isInteractive && onClickPitcher) {
          onClickPitcher()
        }
      }}
    >
      <div
        className="mb-2 flex w-full items-center justify-between gap-1 border-b pb-1 sm:pb-1.5 md:mb-3 md:pb-2"
        style={{ borderColor: tierConfig.accentColor }}
      >
        <span
          className={`font-vintage ${headerSize} flex-1 truncate font-bold uppercase tracking-wider`}
          style={{ color: tierConfig.accentColor }}
        >
          {tierConfig.tierLabel}
        </span>
        <span
          className={`flex-shrink-0 font-vintage text-sm font-bold sm:text-base md:text-lg`}
          style={{ color: tierConfig.accentColor }}
        >
          {player.overall ?? '--'}
        </span>
      </div>

      <div
        className="mb-2 flex flex-1 items-center justify-center border bg-koshien-dark py-3 text-center sm:py-4 md:mb-3 md:py-6"
        style={{ borderColor: `${tierConfig.accentColor}40` }}
      >
        <div className={`font-sports ${jerseySize} font-bold leading-none`} style={{ color: tierConfig.glowColor }}>
          #{player.number || '0'}
        </div>
      </div>

      <h4
        className={`${playerNameSize} mb-2 truncate text-center font-vintage font-bold uppercase tracking-wide text-koshien-chalk md:mb-3`}
      >
        {player.name || 'Loading...'}
      </h4>

      <div className="mb-1 grid grid-cols-3 gap-0.5 sm:gap-1 md:mb-2 md:gap-1">
        {displayStats.map((stat) => (
          <div
            key={stat.label}
            className="flex flex-col items-center justify-center rounded border p-0.5 sm:p-1 md:p-1"
            style={{
              borderColor: `${tierConfig.accentColor}60`,
              backgroundColor: `${tierConfig.accentColor}08`,
            }}
          >
            <span
              className={`font-vintage ${statLabelSize} font-bold uppercase tracking-wider`}
              style={{ color: tierConfig.accentColor }}
            >
              {stat.label}
            </span>
            <span
              className="mt-0.5 font-vintage text-xs font-bold sm:text-sm md:text-base"
              style={{ color: tierConfig.glowColor }}
            >
              {stat.val}
            </span>
          </div>
        ))}
      </div>

      <div
        className="mt-auto border-t pt-1 md:pt-2"
        style={{ borderColor: tierConfig.accentColor }}
      >
        <div className="text-center">
          <div
            className={`font-vintage text-[6px] uppercase tracking-wider sm:text-[7px] md:text-[8px]`}
            style={{ color: tierConfig.accentColor }}
          >
            ⚾ {player.team || 'UNKNOWN'}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
