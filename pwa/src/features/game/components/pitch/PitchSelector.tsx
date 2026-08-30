import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

interface PitchSelectorProps {
  availablePitches: string[]
  selectedPitch: string
  onSelectPitch: (pitch: string) => void
  disabled?: boolean
}

const PULSE = {
  boxShadow: [
    '0 0 8px rgba(197, 160, 89, 0.4)',
    '0 0 16px rgba(197, 160, 89, 0.8)',
    '0 0 8px rgba(197, 160, 89, 0.4)',
  ],
}

const PULSE_IBB = {
  boxShadow: [
    '0 0 8px rgba(197, 160, 89, 0.5)',
    '0 0 18px rgba(247, 245, 240, 0.9)',
    '0 0 8px rgba(197, 160, 89, 0.5)',
  ],
}

export function PitchSelector({
  availablePitches,
  selectedPitch,
  onSelectPitch,
  disabled = false,
}: PitchSelectorProps) {
  const { t } = useTranslation()

  return (
    <div
      className={`flex flex-wrap justify-center gap-1.5 rounded-xs border border-koshien-gold/40 bg-koshien-dark p-1.5 shadow-xl ${
        disabled ? 'pointer-events-none opacity-50' : ''
      }`}
    >
      {availablePitches.map((pitch) => {
        const isSelected = selectedPitch === pitch

        return (
          <motion.button
            key={pitch}
            type="button"
            onClick={() => onSelectPitch(pitch)}
            className={`relative cursor-pointer overflow-hidden rounded-xs border px-3 py-1.5 font-vintage text-[10px] uppercase transition-all ${
              isSelected
                ? 'z-10 border-koshien-gold bg-koshien-green font-bold text-koshien-gold'
                : 'border-koshien-border bg-koshien-dark text-koshien-cream opacity-70 hover:opacity-100'
            }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            animate={isSelected ? PULSE : { boxShadow: '0 0 0px rgba(0,0,0,0)' }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          >
            <span className="relative z-10">{pitch}</span>
          </motion.button>
        )
      })}

      <motion.button
        type="button"
        onClick={() => onSelectPitch('IBB')}
        className={`relative cursor-pointer overflow-hidden rounded-xs border px-2.5 py-1.5 font-vintage text-[10px] uppercase transition-all ${
          selectedPitch === 'IBB'
            ? 'z-10 border-koshien-chalk bg-koshien-gold font-bold text-koshien-dark'
            : 'border-koshien-gold/40 bg-koshien-dark text-koshien-gold opacity-80 hover:opacity-100'
        }`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        animate={selectedPitch === 'IBB' ? PULSE_IBB : { boxShadow: '0 0 0px rgba(0,0,0,0)' }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
      >
        <span className="relative z-10">{t('game.intentional_walk')}</span>
      </motion.button>
    </div>
  )
}