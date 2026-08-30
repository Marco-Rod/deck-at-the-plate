import { motion } from 'framer-motion'

interface StrikeoutCounterProps {
  strikeouts: number
  pitcherName: string
  animate?: boolean
}

export function StrikeoutCounter({ strikeouts = 0, pitcherName = 'Pitcher', animate = false }: StrikeoutCounterProps) {
  return (
    <div className="flex h-full flex-col justify-between rounded-sm border border-koshien-gold/30 bg-koshien-dark/95 p-4 text-center">
      <div className="mb-4 font-vintage text-sm font-bold text-koshien-chalk">{pitcherName}</div>

      <div className="mb-3 font-vintage text-[11px] font-bold tracking-widest text-koshien-gold">K SO</div>

      <div className="flex flex-1 items-center justify-center">
        <motion.div
          className="font-sports text-6xl font-bold text-yellow-400"
          animate={animate ? { scale: [1, 1.15, 1] } : {}}
          transition={{ duration: 0.4 }}
        >
          {strikeouts}
        </motion.div>
      </div>
    </div>
  )
}