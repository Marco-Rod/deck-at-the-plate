import { motion } from 'framer-motion'
import styles from '../../pages/StadiumPage.module.css'

interface PlayerStatsProps {
  stats: Array<{ label: string; value: number }>
  hoveredStat: string | null
  onHoveredStatChange: (stat: string | null) => void
}

export function PlayerStats({ stats, hoveredStat, onHoveredStatChange }: PlayerStatsProps) {
  return (
    <div className={`${styles.playerStats} mb-2 grid grid-cols-3 gap-1 lg:gap-0.5`}>
      {stats.map(({ label, value }) => (
        <motion.div
          key={label}
          onMouseEnter={() => onHoveredStatChange(label)}
          onMouseLeave={() => onHoveredStatChange(null)}
          whileHover={{ scale: 1.05 }}
          className={`rounded border transition-all ${
            hoveredStat === label
              ? 'neon-green border-koshien-dark/40 bg-koshien-green/10'
              : 'border-koshien-light-green/40 bg-koshien-dark'
          } p-1 text-center`}
        >
          <div
            className={`${styles.statLabel} font-vintage text-[8px] uppercase text-koshien-muted sm:text-[9px] lg:text-[7px]`}
          >
            {label}
          </div>
          <motion.div
            animate={{ scale: hoveredStat === label ? 1.1 : 1 }}
            className={`${styles.statValue} font-sports text-xs font-bold text-koshien-gold sm:text-sm lg:text-[14px]`}
          >
            {value}
          </motion.div>
        </motion.div>
      ))}
    </div>
  )
}
