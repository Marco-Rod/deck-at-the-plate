import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

interface StrikeZoneGridProps {
  selectedZone: number
  onSelectZone: (zone: number) => void
  disabled?: boolean
}

const STRIKE_ZONES = [1, 2, 3, 4, 5, 6, 7, 8, 9]

export function StrikeZoneGrid({ selectedZone, onSelectZone, disabled = false }: StrikeZoneGridProps) {
  const { t } = useTranslation()

  return (
    <div
      className={`rounded-xs border-2 border-koshien-gold bg-koshien-dark/95 p-4 text-center shadow-2xl transition-all ${
        disabled ? 'pointer-events-none opacity-40' : ''
      }`}
    >
      <div className="mb-3 border-b border-koshien-gold/30 pb-2">
        <span className="block font-vintage text-[10px] font-bold uppercase text-koshien-gold">
          {t('game.strike_zone')}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {STRIKE_ZONES.map((zone) => {
          const isSelected = selectedZone === zone

          return (
            <motion.button
              key={zone}
              type="button"
              disabled={disabled}
              aria-pressed={isSelected}
              aria-label={t('game.zone', { zone })}
              onClick={() => onSelectZone(zone)}
              className={`relative flex h-16 w-16 cursor-pointer items-center justify-center border font-vintage text-xs overflow-hidden transition-all focus-visible:z-20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
                isSelected
                  ? 'z-10 border-red-600 bg-red-900/30 font-bold text-red-400 shadow-lg'
                  : 'border-koshien-border bg-koshien-dark text-koshien-cream hover:border-white/40'
              }`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <motion.div
                className="pointer-events-none absolute inset-0 rounded-xs border-2 border-white/30"
                animate={{ opacity: [0.3, 0.8, 0.3], scale: [1, 1.1, 1] }}
                transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
                initial={false}
              />

              {isSelected && (
                <>
                  <motion.div
                    className="pointer-events-none absolute inset-0 rounded-xs border-2 border-red-500"
                    animate={{
                      boxShadow: [
                        'inset 0 0 8px rgba(239, 68, 68, 0.3), 0 0 12px rgba(239, 68, 68, 0.5)',
                        'inset 0 0 20px rgba(239, 68, 68, 0.8), 0 0 30px rgba(239, 68, 68, 0.9)',
                        'inset 0 0 8px rgba(239, 68, 68, 0.3), 0 0 12px rgba(239, 68, 68, 0.5)',
                      ],
                    }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                  />

                  <motion.div
                    className="pointer-events-none absolute -inset-1 rounded-xs border-2 border-dashed border-red-500/70"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                  />

                  <motion.div
                    className="pointer-events-none absolute inset-0 rounded-xs border-2 border-red-400"
                    initial={{ boxShadow: '0 0 0px rgba(239, 68, 68, 0.8)' }}
                    animate={{
                      boxShadow: [
                        '0 0 2px rgba(239, 68, 68, 0.8)',
                        '0 0 25px rgba(239, 68, 68, 0.9)',
                        '0 0 2px rgba(239, 68, 68, 0.8)',
                      ],
                    }}
                    transition={{ duration: 0.6, repeat: Infinity, repeatDelay: 1.5, ease: 'easeOut' }}
                  />
                </>
              )}

              <span className="relative z-10 font-bold">Z{zone}</span>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
