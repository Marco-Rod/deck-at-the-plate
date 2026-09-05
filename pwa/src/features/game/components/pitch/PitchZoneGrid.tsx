import { useMemo, useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import { motion } from 'framer-motion'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import type { PitchAttribute, PlayerRole } from '@/shared/api/types'
import { StrikeZoneGrid } from './StrikeZoneGrid'
import { useDialogFocus } from '@/shared/ui/useDialogFocus'

interface PitchZoneGridProps {
  role: PlayerRole
  selectedZone: number
  selectedPitch: string
  onSelectZone: (zone: number) => void
  onSelectPitch: (pitch: string) => void
  repertoire?: PitchAttribute[]
  disabled?: boolean
}

const DEFAULT_REPERTOIRE = ['4-SEAM', 'SLIDER', 'CHANGE']

const PULSE = {
  boxShadow: [
    '0 0 12px rgba(197, 160, 89, 0.5)',
    '0 0 24px rgba(197, 160, 89, 0.9)',
    '0 0 12px rgba(197, 160, 89, 0.5)',
  ],
}

const PULSE_IBB = {
  boxShadow: [
    '0 0 12px rgba(197, 160, 89, 0.6)',
    '0 0 24px rgba(247, 245, 240, 0.9)',
    '0 0 12px rgba(197, 160, 89, 0.6)',
  ],
}

export function PitchZoneGrid({
  role,
  selectedZone,
  selectedPitch,
  onSelectZone,
  onSelectPitch,
  repertoire,
  disabled = false,
}: PitchZoneGridProps) {
  const { t } = useTranslation()
  const [showPitchModal, setShowPitchModal] = useState(false)
  const pitchDialogRef = useRef<HTMLDivElement>(null)
  useDialogFocus({
    active: role === 'PITCHER' && showPitchModal && !disabled,
    containerRef: pitchDialogRef,
    onEscape: () => setShowPitchModal(false),
  })

  const availablePitches = useMemo(() => {
    if (repertoire && repertoire.length > 0) {
      return repertoire.map((pitch) => pitch.pitch_type)
    }
    return DEFAULT_REPERTOIRE
  }, [repertoire])

  const isIBBMode = selectedPitch === 'IBB'

  const handleZoneSelect = (zone: number) => {
    onSelectZone(zone)
    setShowPitchModal(true)
  }

  const handlePitchSelect = (pitch: string) => {
    onSelectPitch(pitch)
    setShowPitchModal(false)
  }

  const handleModalBackdropClick = (event: MouseEvent) => {
    event.stopPropagation()
    setShowPitchModal(false)
  }

  return (
    <div
      className={`relative my-auto flex flex-col items-center gap-3 transition-opacity ${
        disabled ? 'pointer-events-none opacity-40' : ''
      }`}
    >
      <div className="relative">
        <StrikeZoneGrid
          selectedZone={selectedZone}
          onSelectZone={role === 'PITCHER' ? handleZoneSelect : onSelectZone}
          disabled={disabled}
        />
      </div>

      {role === 'PITCHER' && showPitchModal && !disabled &&
        createPortal(
          <motion.div
            className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6 lg:p-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleModalBackdropClick}
          >
            <div className="pointer-events-none fixed inset-0 z-0 bg-black/40 backdrop-blur-sm" />

            <motion.div
              ref={pitchDialogRef}
              role="dialog"
              aria-modal="true"
              aria-labelledby="pitch-selection-title"
              tabIndex={-1}
              className="relative z-[10000] w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-lg border-2 border-koshien-gold bg-gradient-to-b from-koshien-dark to-koshien-dark p-6 shadow-2xl sm:p-8 lg:p-10"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              onClick={(event) => event.stopPropagation()}
            >
              <div className="mb-6 border-b border-koshien-gold/50 pb-4">
                <h3 id="pitch-selection-title" className="text-center font-vintage text-lg font-bold uppercase tracking-wider text-koshien-gold sm:text-xl">
                  {t('game.select_pitch')}
                </h3>
                <p className="mt-2 text-center font-vintage text-xs text-koshien-cream/70 sm:text-sm">
                  {t('game.zone', { zone: selectedZone })}
                </p>
              </div>

              <div className="mb-6 flex flex-wrap justify-center gap-3 sm:gap-4">
                {availablePitches.map((pitch) => {
                  const isSelected = selectedPitch === pitch

                  return (
                    <motion.button
                      key={pitch}
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => handlePitchSelect(pitch)}
                      className={`relative cursor-pointer overflow-hidden rounded-lg border-2 px-5 py-3 font-vintage text-sm font-bold uppercase transition-all sm:px-6 sm:py-4 sm:text-base ${
                        isSelected
                          ? 'scale-105 border-koshien-gold bg-koshien-green text-koshien-gold'
                          : 'border-koshien-border bg-koshien-dark text-koshien-cream hover:scale-105 hover:border-koshien-gold/60'
                      }`}
                      whileHover={{ scale: 1.08 }}
                      whileTap={{ scale: 0.96 }}
                      animate={isSelected ? PULSE : { boxShadow: '0 0 0px rgba(0,0,0,0)' }}
                      transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                    >
                      <span className="relative z-10">{pitch}</span>
                    </motion.button>
                  )
                })}

                <motion.button
                  type="button"
                  aria-pressed={selectedPitch === 'IBB'}
                  onClick={() => handlePitchSelect('IBB')}
                  className={`relative cursor-pointer overflow-hidden rounded-lg border-2 px-5 py-3 font-vintage text-sm font-bold uppercase transition-all sm:px-6 sm:py-4 sm:text-base ${
                    selectedPitch === 'IBB'
                      ? 'scale-105 border-koshien-chalk bg-koshien-gold text-koshien-dark'
                      : 'border-koshien-gold/50 bg-koshien-dark text-koshien-gold hover:scale-105 hover:border-koshien-gold'
                  }`}
                  whileHover={{ scale: 1.08 }}
                  whileTap={{ scale: 0.96 }}
                  animate={selectedPitch === 'IBB' ? PULSE_IBB : { boxShadow: '0 0 0px rgba(0,0,0,0)' }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                >
                  <span className="relative z-10">🏃 IBB</span>
                </motion.button>
              </div>

              <div className="border-t border-koshien-gold/50 pt-4 text-center">
                <p className="font-vintage text-xs text-koshien-cream/60 sm:text-sm">{t('game.click_outside')}</p>
              </div>
            </motion.div>
          </motion.div>,
          document.body,
        )}

      {isIBBMode && (
        <div className="rounded-xs border border-koshien-gold/30 bg-koshien-gold/10 px-3 py-2 text-center">
          <span className="font-vintage text-[9px] font-bold uppercase text-koshien-gold">{t('game.ibb_ready')}</span>
        </div>
      )}
    </div>
  )
}
