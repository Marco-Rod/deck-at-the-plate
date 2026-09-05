import { motion } from 'framer-motion'
import type { PlayerRole } from '@/shared/api/types'

interface StrikeZoneProps {
  selectedZone: number
  setSelectedZone: (zone: number) => void
  selectedPitch?: string
  role: PlayerRole
  disabled: boolean
}

const ZONES = [1, 2, 3, 4, 5, 6, 7, 8, 9]

export function StrikeZone({
  selectedZone,
  setSelectedZone,
  selectedPitch,
  role,
  disabled,
}: StrikeZoneProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.35 }}
      className={`neon-amber flex flex-col border border-koshien-border bg-koshien-dark/60 p-2 sm:p-2 lg:p-1 ${disabled ? 'pointer-events-none opacity-40' : ''}`}
    >
      <div className="mb-1 text-center font-vintage text-[10px] uppercase text-koshien-gold sm:mb-2 sm:text-xs lg:mb-1 lg:text-[9px]">
        {role === 'PITCHER' ? 'ELIGE ZONA' : 'ZONA DE STRIKE'}
      </div>
      <div className="flex flex-1 items-center justify-center">
        <div className="grid aspect-square w-full grid-cols-3 gap-1 lg:gap-0.5">
          {ZONES.map((zone) => {
            const isSelected = zone === selectedZone
            const showPitch = role === 'PITCHER' && isSelected && selectedPitch
            return (
              <motion.button
                key={zone}
                type="button"
                disabled={disabled}
                aria-pressed={isSelected}
                aria-label={`Zona ${zone}`}
                onClick={() => setSelectedZone(zone)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                layoutId={`zone-${zone}`}
                className={`zone-ripple flex items-center justify-center rounded border transition-all focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-koshien-gold ${isSelected ? 'border-2 border-koshien-red bg-koshien-red/20 shadow-[0_0_8px_rgba(255,85,79,0.4)]' : 'zone-border border bg-koshien-dark/40 hover:border-koshien-gold/60'}`}
              >
                {showPitch ? (
                  <span className="px-0.5 font-sports text-[10px] font-bold leading-tight text-koshien-gold sm:text-xs lg:text-[9px]">
                    {selectedPitch}
                  </span>
                ) : (
                  <span className="font-sports text-xs font-bold text-koshien-chalk sm:text-sm lg:text-[9px]">
                    {isSelected ? '🎯' : ''}
                  </span>
                )}
              </motion.button>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}
