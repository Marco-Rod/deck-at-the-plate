import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import type { PlayerRole } from '@/shared/api/types'
import styles from '../../pages/StadiumPage.module.css'
import { PlayerStats } from './PlayerStats'
import type { BatterSummary, PitcherSummary } from './playerPanelTypes'

function rarityClass(rarity: string): string {
  const value = `rarity-${rarity.toLowerCase()}`
  return [
    'rarity-common',
    'rarity-bronze',
    'rarity-silver',
    'rarity-gold',
    'rarity-diamond',
  ].includes(value)
    ? value
    : 'rarity-common'
}

interface CardShellProps {
  kind: 'PITCHER' | 'BATTER'
  active: boolean
  name: string
  number: string
  overall: number
  rarity: string
  stats: Array<{ label: string; value: number }>
  hoveredStat: string | null
  onHoveredStatChange: (stat: string | null) => void
  delay: number
  footer?: ReactNode
}

function CardShell({
  kind,
  active,
  name,
  number,
  overall,
  rarity,
  stats,
  hoveredStat,
  onHoveredStatChange,
  delay,
  footer,
}: CardShellProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className={`${rarityClass(rarity)} flex flex-col border border-koshien-dark/40 bg-koshien-dark/60 p-2 sm:p-3 lg:p-2`}
    >
      <div className={`${styles.playerCardContent} flex-1`}>
        <div
          className={`${styles.playerCardHeader} mb-1 flex items-center justify-between border-b border-white/10 pb-1`}
        >
          <span className="font-vintage text-[9px] uppercase text-koshien-muted sm:text-xs lg:text-[10px] desktop:text-[12px]">
            {kind} {active ? '●' : ''}
          </span>
          <span className="font-sports text-xs font-bold text-koshien-gold sm:text-sm lg:text-[14px] desktop:text-[18px]">
            {overall}
          </span>
        </div>
        <motion.div
          animate={{ scale: 1 }}
          initial={{ scale: 0.8 }}
          className={`${styles.playerIdentity} mb-2 text-center font-sports text-2xl font-bold text-koshien-gold sm:text-3xl lg:text-xl`}
        >
          <span className={styles.playerHash}>#</span>
          <span className={styles.playerNumber}>{number}</span>
        </motion.div>
        <div
          className={`${styles.playerName} mb-2 truncate text-center font-vintage text-[10px] font-bold uppercase text-koshien-chalk sm:text-xs lg:text-[8px]`}
        >
          {name}
        </div>
        <PlayerStats
          stats={stats}
          hoveredStat={hoveredStat}
          onHoveredStatChange={onHoveredStatChange}
        />
        {footer}
      </div>
    </motion.div>
  )
}

interface PitcherCardProps {
  pitcher: PitcherSummary
  role: PlayerRole
  hoveredStat: string | null
  setHoveredStat: (stat: string | null) => void
  onChangePitcher: () => void
}

export function PitcherCard({
  pitcher,
  role,
  hoveredStat,
  setHoveredStat,
  onChangePitcher,
}: PitcherCardProps) {
  const isPitching = role === 'PITCHER'
  const footer = isPitching ? (
    <button
      type="button"
      onClick={onChangePitcher}
      disabled={pitcher.pitchCount < 5}
      className="mt-auto hidden w-full items-center justify-center border border-koshien-gold/60 bg-koshien-dark/70 px-2 py-1 font-vintage text-[9px] uppercase tracking-wider text-koshien-gold transition hover:bg-koshien-gold/15 disabled:cursor-not-allowed disabled:border-koshien-muted/30 disabled:text-koshien-muted/50 desktop:flex"
    >
      {pitcher.pitchCount < 5 ? `${5 - pitcher.pitchCount} lanz. para cambio` : 'Cambiar lanzador'}
    </button>
  ) : undefined

  return (
    <CardShell
      kind="PITCHER"
      active={isPitching}
      name={pitcher.name}
      number={pitcher.number}
      overall={pitcher.overall}
      rarity={pitcher.rarity}
      stats={[
        { label: 'VEL', value: pitcher.velocity },
        { label: 'CTRL', value: pitcher.control },
        { label: 'MOV', value: pitcher.movement },
      ]}
      hoveredStat={hoveredStat}
      onHoveredStatChange={setHoveredStat}
      delay={0.3}
      footer={footer}
    />
  )
}

export function BatterCard({
  batter,
  role,
  hoveredStat,
  setHoveredStat,
}: {
  batter: BatterSummary
  role: PlayerRole
  hoveredStat: string | null
  setHoveredStat: (stat: string | null) => void
}) {
  return (
    <CardShell
      kind="BATTER"
      active={role === 'BATTER'}
      name={batter.name}
      number={batter.number}
      overall={batter.overall}
      rarity={batter.rarity}
      stats={[
        { label: 'CON', value: batter.contact },
        { label: 'PWR', value: batter.power },
        { label: 'SPD', value: batter.speed },
      ]}
      hoveredStat={hoveredStat}
      onHoveredStatChange={setHoveredStat}
      delay={0.4}
    />
  )
}
