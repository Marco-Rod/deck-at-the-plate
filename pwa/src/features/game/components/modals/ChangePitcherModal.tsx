import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import type { PlayerGameData } from '@/shared/api/types'

interface BullpenPitcher extends PlayerGameData {
  already_used?: boolean
}

interface ChangePitcherModalProps {
  isOpen: boolean
  onClose: () => void
  currentPitcher: PlayerGameData | null
  availablePitchers: BullpenPitcher[]
  onConfirm: (newPitcherId: string) => Promise<void>
  isLoading?: boolean
}

const RARITY_COLOR: Record<string, string> = {
  DIAMOND: 'text-cyan-300',
  GOLD: 'text-koshien-gold',
  SILVER: 'text-slate-300',
  BRONZE: 'text-orange-400',
  COMMON: 'text-[#A89968]',
}

export function ChangePitcherModal({
  isOpen,
  onClose,
  currentPitcher,
  availablePitchers,
  onConfirm,
  isLoading = false,
}: ChangePitcherModalProps) {
  const { t } = useTranslation()
  const [selectedPitcherId, setSelectedPitcherId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async () => {
    if (!selectedPitcherId) {
      setError(t('game.select_pitcher_error'))
      return
    }
    if (selectedPitcherId === currentPitcher?.id) {
      setError(t('game.different_pitcher_error'))
      return
    }
    try {
      setError(null)
      await onConfirm(selectedPitcherId)
      onClose()
    } catch {
      setError(t('game.change_error'))
    }
  }

  const selectedPitcher = availablePitchers.find((p) => p.id === selectedPitcherId)
  const freshCount = availablePitchers.filter((p) => !p.already_used).length

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/75"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 16 }}
            transition={{ duration: 0.18 }}
            className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="pointer-events-auto w-full max-w-3xl rounded-xl border-2 border-koshien-gold/50 bg-[#0F1419]/95 shadow-2xl backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-koshien-gold/30 px-6 py-4">
                <h2 className="font-vintage text-xl font-bold tracking-wide text-koshien-cream">
                  {t('game.change_pitcher_title')}
                </h2>
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isLoading}
                  className="text-xl font-bold leading-none text-koshien-gold hover:text-koshien-chalk disabled:opacity-50"
                >
                  ✕
                </button>
              </div>

              <div className="flex flex-col gap-0 divide-y divide-koshien-gold/20 md:flex-row md:divide-x md:divide-y-0">
                <div className="flex flex-shrink-0 flex-col gap-4 px-5 py-4 md:w-56">
                  <div>
                    <p className="mb-2 font-vintage text-[10px] uppercase tracking-widest text-koshien-gold">
                      {t('game.on_mound')}
                    </p>
                    <PitcherMiniCard pitcher={currentPitcher} dimmed />
                  </div>
                  <div>
                    <p className="mb-2 font-vintage text-[10px] uppercase tracking-widest text-koshien-gold">
                      {t('game.selected')}
                    </p>
                    {selectedPitcher ? (
                      <PitcherMiniCard pitcher={selectedPitcher} highlight />
                    ) : (
                      <div className="flex h-20 items-center justify-center rounded border border-dashed border-koshien-gold/25 font-vintage text-xs text-[#A89968]">
                        {t('game.choose_pitcher')}
                      </div>
                    )}
                  </div>
                </div>

                <div className="min-h-0 flex-1 px-5 py-4">
                  <p className="mb-3 font-vintage text-[10px] uppercase tracking-widest text-koshien-gold">
                    {t('game.bullpen')}{' '}
                    <span className="text-koshien-cream">{freshCount}</span> {t('game.available')}
                    {availablePitchers.length > freshCount && (
                      <span className="text-[#A89968]">
                        {' '}· {availablePitchers.length - freshCount} {t('game.already_used_count')}
                      </span>
                    )}
                  </p>

                  {availablePitchers.length === 0 ? (
                    <div className="flex h-32 items-center justify-center font-vintage text-sm text-[#A89968]">
                      {t('game.no_bullpen')}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {availablePitchers.map((pitcher) => {
                        const isSelected = selectedPitcherId === pitcher.id
                        const isUsed = !!pitcher.already_used
                        const rarityClass = RARITY_COLOR[pitcher.rarity || 'COMMON'] || RARITY_COLOR.COMMON
                        const pitchStats = pitcher.stats?.slice(0, 3) ?? []

                        return (
                          <motion.button
                            key={pitcher.id}
                            type="button"
                            onClick={() => !isUsed && setSelectedPitcherId(pitcher.id)}
                            whileTap={isUsed ? {} : { scale: 0.97 }}
                            disabled={isUsed}
                            className={`relative rounded-lg border px-3 py-2.5 text-left transition-all duration-150 ${
                              isUsed
                                ? 'cursor-not-allowed border-koshien-gold/10 bg-koshien-dark opacity-45'
                                : isSelected
                                  ? 'border-koshien-gold bg-koshien-gold/10 shadow-[0_0_8px_rgba(255,215,0,0.25)]'
                                  : 'border-koshien-gold/25 bg-koshien-dark hover:border-koshien-gold/55 hover:bg-[#1A1F24]'
                            }`}
                          >
                            <div className="mb-1 flex items-center justify-between gap-2">
                              <span
                                className={`truncate text-sm font-bold leading-tight ${
                                  isUsed ? 'text-[#5A5A5A]' : 'text-koshien-cream'
                                }`}
                              >
                                #{pitcher.number} {pitcher.name}
                              </span>
                              <span
                                className={`flex-shrink-0 text-lg font-black ${
                                  isUsed ? 'text-[#4A4A4A]' : 'text-koshien-gold'
                                }`}
                              >
                                {pitcher.overall}
                              </span>
                            </div>

                            <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[11px]">
                              <span
                                className={`rounded px-1.5 py-0.5 font-vintage text-[10px] font-bold ${
                                  isUsed ? 'bg-[#2A2A2A] text-[#555]' : 'bg-koshien-gold/20 text-koshien-gold'
                                }`}
                              >
                                {pitcher.position}
                              </span>
                              {isUsed ? (
                                <span className="font-vintage text-[10px] font-bold tracking-wide text-red-500/70">
                                  {t('game.your_used')}
                                </span>
                              ) : (
                                <span className={`font-vintage ${rarityClass}`}>{pitcher.rarity}</span>
                              )}
                            </div>

                            {!isUsed && pitchStats.length > 0 && (
                              <div className="flex gap-3 font-vintage text-[10px] text-[#A89968]">
                                {pitchStats.map((stat) => (
                                  <span key={stat.label}>
                                    <span className="text-koshien-gold/70">{stat.label}</span>{' '}
                                    <span className="text-koshien-cream">{stat.val}</span>
                                  </span>
                                ))}
                              </div>
                            )}

                            {isSelected && !isUsed && (
                              <span className="absolute top-2 right-2 text-xs text-koshien-gold">✔</span>
                            )}
                          </motion.button>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col items-center gap-3 border-t border-koshien-gold/20 px-6 py-4 sm:flex-row">
                <AnimatePresence>
                  {error && (
                    <motion.p
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      className="flex-1 font-vintage text-sm text-red-400"
                    >
                      ⚠ {error}
                    </motion.p>
                  )}
                </AnimatePresence>
                <div className="ml-auto flex gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={isLoading}
                    className="rounded-lg border border-koshien-gold/50 px-4 py-2 font-vintage text-sm font-bold text-koshien-gold transition-colors hover:bg-koshien-gold/10 disabled:opacity-50"
                  >
                    {t('game.cancel')}
                  </button>
                  <motion.button
                    type="button"
                    onClick={handleConfirm}
                    disabled={isLoading || !selectedPitcherId || selectedPitcherId === currentPitcher?.id}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    className="rounded-lg bg-koshien-gold px-6 py-2 font-vintage text-sm font-bold text-koshien-dark transition-colors hover:bg-koshien-chalk disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {isLoading ? (
                      <span className="flex items-center gap-2">
                        <span className="inline-block animate-spin">⟳</span>
                        {t('game.changing')}
                      </span>
                    ) : (
                      t('game.confirm_change')
                    )}
                  </motion.button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

interface PitcherMiniCardProps {
  pitcher: PlayerGameData | null
  highlight?: boolean
  dimmed?: boolean
}

function PitcherMiniCard({ pitcher, highlight = false, dimmed = false }: PitcherMiniCardProps) {
  if (!pitcher) return null
  const rarityClass = RARITY_COLOR[pitcher.rarity || 'COMMON'] || RARITY_COLOR.COMMON

  return (
    <div
      className={`rounded-lg border px-3 py-2.5 ${
        highlight
          ? 'border-koshien-gold bg-koshien-gold/10'
          : dimmed
            ? 'border-koshien-gold/20 bg-koshien-dark'
            : 'border-koshien-gold/30 bg-koshien-dark'
      }`}
    >
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className={`truncate text-sm font-bold ${dimmed ? 'text-[#A89968]' : 'text-koshien-cream'}`}>
          #{pitcher.number} {pitcher.name}
        </span>
        <span className={`flex-shrink-0 text-lg font-black text-koshien-gold`}>
          {pitcher.overall}
        </span>
      </div>
      <div className="flex items-center gap-2 text-[10px]">
        <span className="rounded bg-koshien-gold/15 px-1.5 py-0.5 font-vintage font-bold text-koshien-gold">
          {pitcher.position}
        </span>
        <span className={`font-vintage ${rarityClass}`}>{pitcher.rarity}</span>
      </div>
    </div>
  )
}