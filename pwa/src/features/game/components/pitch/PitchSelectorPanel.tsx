import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import type { PitchAttribute } from '@/shared/api/types'

interface PitchSelectorPanelProps {
  repertoire: PitchAttribute[] | null | undefined
  selectedPitch: string
  onSelectPitch: (pitch: string) => void
  disabled?: boolean
}

export function PitchSelectorPanel({
  repertoire,
  selectedPitch,
  onSelectPitch,
  disabled = false,
}: PitchSelectorPanelProps) {
  const { t } = useTranslation()

  const pitches = (repertoire ?? [])
    .slice(0, 4)
    .map((p) => ({ type: p.pitch_type, velocity: p.velocity ?? 0 }))

  return (
    <div className="w-full">
      <div
        className={`neon-amber grid grid-cols-2 gap-1.5 rounded border border-koshien-gold/40 bg-koshien-dark p-1.5 shadow-xl ${
          disabled ? 'pointer-events-none opacity-50' : ''
        }`}
      >
        {pitches.map((pitch) => {
          const isSelected = selectedPitch === pitch.type
          return (
            <motion.button
              key={pitch.type}
              type="button"
              onClick={() => onSelectPitch(pitch.type)}
              className={`relative cursor-pointer overflow-hidden rounded border px-2 py-2 text-center transition-all ${
                isSelected
                  ? 'z-10 border-koshien-gold bg-koshien-green'
                  : 'border-koshien-border bg-koshien-dark text-koshien-cream opacity-75 hover:opacity-100'
              }`}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.95 }}
            >
              <span
                className={`block font-sports text-sm font-bold leading-none ${
                  isSelected ? 'text-koshien-gold' : 'text-koshien-chalk'
                }`}
              >
                {pitch.type}
              </span>
              <span
                className={`mt-1 block font-vintage text-[10px] uppercase tracking-wider ${
                  isSelected ? 'text-koshien-dark' : 'text-koshien-muted'
                }`}
              >
                {pitch.velocity > 0 ? `${pitch.velocity} MPH` : '–'}
              </span>
            </motion.button>
          )
        })}
        {pitches.length === 0 && (
          <div className="col-span-2 py-3 text-center font-vintage text-[10px] uppercase tracking-widest text-koshien-muted">
            {t('game.no_pitches') || 'Sin lanzamientos'}
          </div>
        )}
      </div>
    </div>
  )
}
