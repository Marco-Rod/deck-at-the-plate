import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import type { PlayerRole } from '@/shared/api/types'
import styles from '../../pages/StadiumPage.module.css'

interface HeaderProps {
  homeTeamName: string
  isConnected: boolean
  onQuit: () => void
}

export function Header({ homeTeamName, isConnected, onQuit }: HeaderProps) {
  const { t } = useTranslation()
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-2 flex items-center justify-between lg:mb-0"
    >
      <h1 className="font-sports text-2xl font-bold uppercase tracking-wider text-koshien-chalk sm:text-3xl lg:text-2xl">
        {homeTeamName} VS CPU
      </h1>
      <div className="flex items-center gap-3">
        <span
          className={`hidden font-vintage text-[11px] font-bold uppercase tracking-widest sm:inline ${
            isConnected
              ? 'text-[#4ef09a] drop-shadow-[0_0_6px_rgba(78,240,154,0.8)]'
              : 'text-koshien-red'
          }`}
        >
          {isConnected ? t('game.live') : t('game.disconnected')}
        </span>
        <motion.button
          whileHover={{ scale: 1.05, borderColor: '#FF554F' }}
          whileTap={{ scale: 0.95 }}
          onClick={onQuit}
          className="rounded border border-koshien-red bg-koshien-dark px-4 py-2 text-sm font-bold uppercase text-koshien-red transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-red sm:px-6 sm:py-2.5 lg:px-4 lg:py-2 lg:text-xs"
          aria-label="Finalizar partida"
        >
          <span className="text-xs sm:text-sm lg:text-xs">🎬 FINALIZAR</span>
        </motion.button>
      </div>
    </motion.div>
  )
}

interface ScoreboardProps {
  homeTeamName: string
  awayTeamName: string
  homeScore: number
  awayScore: number
}

export function Scoreboard({ homeTeamName, awayTeamName, homeScore, awayScore }: ScoreboardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="neon-amber border border-koshien-border bg-koshien-dark/40 p-3 sm:p-4 lg:p-2"
    >
      <div className="mb-2 flex items-center justify-between border-b border-koshien-border/30 pb-2">
        <span className="truncate font-vintage text-[10px] uppercase tracking-widest text-koshien-gold">
          {homeTeamName}
        </span>
        <span className="font-sports text-3xl font-bold text-koshien-chalk lg:text-2xl">
          {homeScore}
        </span>
      </div>
      <div className="mb-2 flex items-center justify-between border-b border-koshien-border/30 pb-2">
        <span className="truncate font-vintage text-[10px] uppercase tracking-widest text-koshien-muted">
          {awayTeamName}
        </span>
        <span className="font-sports text-3xl font-bold text-koshien-chalk lg:text-2xl">
          {awayScore}
        </span>
      </div>
    </motion.div>
  )
}

interface GameSituationProps {
  inning: number
  isTop: boolean
  balls: number
  strikes: number
  outs: number
  bases: { first: boolean; second: boolean; third: boolean }
  role: PlayerRole
}

function CountDots({
  total,
  value,
  colorClass,
}: {
  total: number
  value: number
  colorClass: string
}) {
  return (
    <div className={styles.countDots}>
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`${styles.countDot} ${colorClass} ${i < value ? styles.countDotActive : ''}`}
        />
      ))}
    </div>
  )
}

export function GameSituation({
  inning,
  isTop,
  balls,
  strikes,
  outs,
  bases,
  role,
}: GameSituationProps) {
  const count = [
    { label: 'BALLS', total: 4, value: balls, colorClass: String(styles.countBalls) },
    { label: 'STRIKES', total: 2, value: strikes, colorClass: String(styles.countStrikes) },
    { label: 'OUTS', total: 2, value: outs, colorClass: String(styles.countOuts) },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className={`${styles.gameSituation} neon-amber border border-koshien-border bg-koshien-dark/40 p-3 sm:p-4`}
    >
      <div className={styles.countRow}>
        {count.map(({ label, total, value, colorClass }) => (
          <div key={label} className="text-center">
            <div className={styles.countLabel}>{label}</div>
            <CountDots total={total} value={value} colorClass={colorClass} />
          </div>
        ))}
      </div>
      <div className={`${styles.situationDivider} ${styles.situationMainDivider}`} />
      <div className={`${styles.situationZone} ${styles.situationInningZone}`}>
        <div className={styles.situationInning}>
          <div className={styles.situationLabel}>INNING</div>
          <div className={styles.situationValue}>{inning}/3</div>
          <div className={styles.situationLabel}>{isTop ? '▲ TOP' : '▼ BOT'}</div>
        </div>
      </div>
      <div className={`${styles.situationDivider} ${styles.situationRowDivider}`} />
      <div className={`${styles.situationZone} ${styles.situationBasesZone}`}>
        <div className={styles.situationLabel}>
          {role === 'PITCHER' ? 'TU PICHAS' : 'TU BATEAS'}
        </div>
        <div className="mt-1 flex justify-center">
          <BasesDiamond bases={bases} />
        </div>
      </div>
    </motion.div>
  )
}

function BasesDiamond({ bases }: { bases: { first: boolean; second: boolean; third: boolean } }) {
  return (
    <svg
      viewBox="0 0 60 60"
      className="h-12 w-12 sm:h-14 sm:w-14 lg:h-10 lg:w-10"
      aria-hidden="true"
    >
      <g className={styles.basesDiamondGraphic}>
        <path d="M 30 10 L 50 30 L 30 50 L 10 30 Z" fill="none" stroke="#F2A13A" strokeWidth="1" />
        <motion.circle
          cx="30"
          cy="10"
          fill={bases.second ? '#F2A13A' : 'none'}
          initial={{ r: 2 }}
          animate={{ r: bases.second ? 3.5 : 2 }}
          transition={{ repeat: bases.second ? Infinity : 0, repeatType: 'reverse', duration: 1 }}
        />
        <motion.circle
          cx="50"
          cy="30"
          fill={bases.first ? '#F2A13A' : 'none'}
          initial={{ r: 2 }}
          animate={{ r: bases.first ? 3.5 : 2 }}
          transition={{
            repeat: bases.first ? Infinity : 0,
            repeatType: 'reverse',
            duration: 1,
            delay: 0.2,
          }}
        />
        <circle cx="30" cy="50" r="2" fill="none" />
        <motion.circle
          cx="10"
          cy="30"
          fill={bases.third ? '#F2A13A' : 'none'}
          initial={{ r: 2 }}
          animate={{ r: bases.third ? 3.5 : 2 }}
          transition={{
            repeat: bases.third ? Infinity : 0,
            repeatType: 'reverse',
            duration: 1,
            delay: 0.1,
          }}
        />
        <circle cx="30" cy="30" r="1.5" fill="#F2A13A" opacity="0.5" />
      </g>
    </svg>
  )
}
