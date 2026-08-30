import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

interface PitcherStaminaBarProps {
  pitchCount?: number
  fatigueLevel?: number
  totalInnings?: number
  basePitcherStats?: {
    velocidad?: number
    control?: number
    movimiento?: number
  }
}

interface FatigueStats {
  velocidad: number
  control: number
  movimiento: number
}

const getPitchThreshold = (totalInnings = 9): number => {
  const THRESHOLDS: Record<number, number> = {
    3: 18,
    6: 40,
    9: 60,
  }

  if (THRESHOLDS[totalInnings]) {
    return THRESHOLDS[totalInnings]
  }

  return Math.max(6, Math.round((60.0 / 9.0) * totalInnings))
}

const calculateFatigueStats = (
  baseStats: { velocidad?: number; control?: number; movimiento?: number },
  pitchCount = 0,
): FatigueStats => {
  const PITCH_THRESHOLD = 60
  const FATIGUE_PENALTY_STEP = 15

  const base = {
    velocidad: baseStats.velocidad || 75,
    control: baseStats.control || 75,
    movimiento: baseStats.movimiento || 75,
  }

  if (pitchCount <= PITCH_THRESHOLD) {
    return base
  }

  const extraPitches = pitchCount - PITCH_THRESHOLD
  const penalty = Math.max(
    0.5,
    1.0 - 0.03 * (Math.floor(extraPitches / FATIGUE_PENALTY_STEP) + 1),
  )

  return {
    velocidad: Math.round(base.velocidad * penalty),
    control: Math.round(base.control * penalty),
    movimiento: Math.round(base.movimiento * penalty),
  }
}

const getStaminaColor = (
  fatigueLevel: number,
): { color: string; labelKey: string; bgColor: string } => {
  if (fatigueLevel < 40) {
    return { color: '#22C55E', labelKey: 'game.fresh', bgColor: '#0F766E' }
  }
  if (fatigueLevel < 70) {
    return { color: '#EAB308', labelKey: 'game.moderate', bgColor: '#713F12' }
  }
  if (fatigueLevel < 85) {
    return { color: '#F97316', labelKey: 'game.very_tired', bgColor: '#7C2D12' }
  }
  return { color: '#EF4444', labelKey: 'game.critical', bgColor: '#7F1D1D' }
}

export function PitcherStaminaBar({
  pitchCount = 0,
  fatigueLevel = 0,
  totalInnings = 9,
  basePitcherStats = {},
}: PitcherStaminaBarProps) {
  const { t } = useTranslation()
  const currentStats = useMemo(
    () => calculateFatigueStats(basePitcherStats, pitchCount),
    [basePitcherStats, pitchCount],
  )

  const staminaColor = useMemo(() => getStaminaColor(fatigueLevel), [fatigueLevel])

  const getPenalty = (stat: keyof FatigueStats): number => {
    const base = basePitcherStats[stat] || 75
    const current = currentStats[stat]
    return Math.round(((base - current) / base) * 100)
  }

  const velocityPenalty = getPenalty('velocidad')
  const controlPenalty = getPenalty('control')
  const movementPenalty = getPenalty('movimiento')

  const statCell = (
    label: string,
    value: number,
    penalty: number,
  ) => (
    <motion.div
      className="flex flex-col items-center gap-1 rounded-xs border p-1.5 sm:p-2 md:p-2.5"
      style={{
        borderColor: penalty > 0 ? '#EF4444' : '#C5A059',
        backgroundColor: penalty > 0 ? '#1F0F0F' : '#121619',
      }}
      animate={{
        boxShadow:
          penalty > 0
            ? '0 0 8px rgba(239, 68, 68, 0.3)'
            : '0 0 8px rgba(197, 160, 89, 0.1)',
      }}
    >
      <span className="font-vintage text-[7px] font-bold uppercase text-koshien-cream/70 sm:text-[8px] md:text-[9px]">
        {label}
      </span>
      <span className="font-vintage text-xs font-bold text-koshien-gold sm:text-sm md:text-base">{value}</span>
      {penalty > 0 && (
        <span className="font-vintage text-[7px] font-bold text-red-500 sm:text-[8px] md:text-[9px]">
          -{penalty}%
        </span>
      )}
    </motion.div>
  )

  return (
    <div className="flex w-full flex-col gap-2 rounded-lg border border-koshien-gold/30 bg-koshien-dark/60 p-2 sm:gap-3 sm:p-3 md:p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-vintage text-[10px] font-bold uppercase tracking-wider text-koshien-cream sm:text-xs md:text-sm">
          {t('game.physique')}
        </h3>
        <span
          className="rounded-xs px-2 py-1 font-vintage text-[8px] font-bold uppercase tracking-wide sm:text-[9px] md:text-[10px]"
          style={{ color: staminaColor.color, backgroundColor: staminaColor.bgColor }}
        >
          {t(staminaColor.labelKey)}
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <div className="h-4 w-full overflow-hidden rounded-full border border-koshien-gold/40 bg-koshien-dark/80 sm:h-5 md:h-6">
          <motion.div
            className="h-full rounded-full"
            style={{ backgroundColor: staminaColor.color }}
            initial={{ width: '0%' }}
            animate={{ width: `${fatigueLevel}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          >
            <div className="h-full w-full bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          </motion.div>
        </div>

        <div className="flex items-center justify-between px-1">
          <span className="font-vintage text-[8px] text-koshien-cream/70 sm:text-[9px] md:text-[10px]">
            {t('game.fatigue')}
          </span>
          <span
            className="font-vintage text-[8px] font-bold sm:text-[9px] md:text-[10px]"
            style={{ color: staminaColor.color }}
          >
            {fatigueLevel.toFixed(1)}%
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 rounded-xs border border-koshien-gold/20 bg-koshien-dark/60 px-2 py-1.5">
        <span className="font-vintage text-[8px] uppercase tracking-wide text-koshien-cream/70 sm:text-[9px] md:text-[10px]">
          {t('game.pitches')}
        </span>
        <div className="flex items-baseline gap-1">
          <span className="font-vintage text-xs font-bold text-koshien-gold sm:text-sm md:text-base">
            {pitchCount}
          </span>
          <span className="font-vintage text-[8px] text-koshien-cream/50 sm:text-[9px] md:text-[10px]">
            {t('game.threshold', { threshold: getPitchThreshold(totalInnings) })}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-1 sm:gap-1.5">
        {statCell('VELO', currentStats.velocidad, velocityPenalty)}
        {statCell('CTRL', currentStats.control, controlPenalty)}
        {statCell('MVTO', currentStats.movimiento, movementPenalty)}
      </div>

      {fatigueLevel > 85 && (
        <motion.div
          className="rounded-xs bg-red-900/40 px-2 py-1.5 text-center border border-red-500/50"
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <p className="font-vintage text-[8px] font-bold uppercase text-red-500 sm:text-[9px] md:text-[10px]">
            {t('game.change_pitcher_warning')}
          </p>
        </motion.div>
      )}
    </div>
  )
}