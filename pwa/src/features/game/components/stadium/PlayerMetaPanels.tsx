import { motion } from 'framer-motion'
import styles from '../../pages/StadiumPage.module.css'

interface PitcherMeta {
  stamina: number
  pitchCount: number
}

interface BatterPreview {
  number: string
  name: string
  contact: number
  power: number
  speed: number
}

export function PitcherMetaBar({ pitcher }: { pitcher: PitcherMeta }) {
  return (
    <motion.div
      className={`${styles.pitcherMeta} flex flex-col justify-center gap-1 border border-koshien-dark/40 bg-koshien-dark/60 p-2 sm:p-3 lg:p-2`}
    >
      <div className="flex items-center justify-between">
        <span className="font-sports text-[10px] font-bold uppercase tracking-wider text-koshien-gold sm:text-sm lg:text-[9px]">
          STAMINA {pitcher.stamina}%
        </span>
        <span className="font-vintage text-[10px] uppercase text-koshien-cream sm:text-sm lg:text-[9px]">
          ⚾ {pitcher.pitchCount} LANZ.
        </span>
      </div>
      <div className="h-1 w-full overflow-hidden rounded bg-koshien-dark/50 lg:h-[3px]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, Math.max(0, pitcher.stamina))}%` }}
          transition={{ duration: 0.8 }}
          className="h-full bg-gradient-to-r from-koshien-green to-koshien-orange"
        />
      </div>
    </motion.div>
  )
}

export function NextBatterPreview({ nextBatter }: { nextBatter: BatterPreview }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.45 }}
      className={`${styles.nextBatter} neon-green border-2 border-koshien-light-green bg-koshien-green/20`}
    >
      <div className="flex items-center justify-between">
        <span className="font-vintage text-[9px] font-bold uppercase tracking-wider text-koshien-cream lg:text-[8px] desktop:text-[clamp(0.875rem,2.5dvh,1.5rem)]">
          SIG
        </span>
        <motion.span
          animate={{ x: [0, 2, 0] }}
          transition={{ repeat: Infinity, duration: 1 }}
          className="text-[9px] text-koshien-cream desktop:text-[clamp(0.875rem,2.5dvh,1.5rem)]"
        >
          ▶
        </motion.span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="font-sports text-sm font-bold text-koshien-gold lg:text-xs desktop:text-[clamp(1.25rem,3dvh,2rem)]">
          #{nextBatter.number}
        </span>
        <span className="truncate font-vintage text-xs font-bold uppercase text-koshien-chalk lg:text-[11px] desktop:text-[clamp(1rem,2.5dvh,1.75rem)]">
          {nextBatter.name}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {[
          { label: 'C', value: nextBatter.contact },
          { label: 'P', value: nextBatter.power },
          { label: 'V', value: nextBatter.speed },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <div className="font-vintage text-[8px] uppercase text-koshien-chalk/70 lg:text-[7px] desktop:text-[clamp(0.75rem,2dvh,1.25rem)]">
              {label}
            </div>
            <div className="font-sports text-sm font-bold text-koshien-light-green lg:text-xs desktop:text-[clamp(1rem,2.5dvh,1.75rem)]">
              {value}
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
