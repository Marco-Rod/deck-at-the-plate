import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import type { PlayerGameData } from '@/shared/api/types'

interface BullpenPitcher extends PlayerGameData {
  already_used?: boolean
}

interface RivalPitcherChangeModalProps {
  isOpen: boolean
  oldPitcher: PlayerGameData | null
  newPitcher: PlayerGameData | null
  onAccept: () => void
  availablePitchers?: BullpenPitcher[]
  onSelectPitcher?: (pitcherId: string) => Promise<void>
  isLoading?: boolean
}

const RARITY_COLOR: Record<string, string> = {
  DIAMOND: 'text-cyan-300',
  GOLD: 'text-koshien-gold',
  SILVER: 'text-slate-300',
  BRONZE: 'text-orange-400',
  COMMON: 'text-[#A89968]',
}

export function RivalPitcherChangeModal({
  isOpen,
  oldPitcher,
  newPitcher,
  onAccept,
  availablePitchers = [],
  onSelectPitcher,
  isLoading = false,
}: RivalPitcherChangeModalProps) {
  const { t } = useTranslation()
  const [selectedPitcherId, setSelectedPitcherId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!oldPitcher) return null

  if (newPitcher && (!availablePitchers || availablePitchers.length === 0)) {
    return (
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
              onClick={onAccept}
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center"
            >
              <div className="pointer-events-auto mx-4 w-full max-w-lg rounded-lg border-2 border-koshien-gold/60 bg-gradient-to-br from-[#1A1D23] via-[#0F1219] to-[#0A0D0F] p-6 shadow-2xl sm:p-8 md:p-10">
                <div className="mb-6 text-center">
                  <h2 className="mb-2 font-vintage text-lg font-bold uppercase tracking-wider text-koshien-gold sm:text-xl md:text-2xl">
                    {t('game.rival_change_title')}
                  </h2>
                  <p className="text-xs text-[#A89968] sm:text-sm">{t('game.rival_change_msg')}</p>
                </div>

                <div className="mb-8 space-y-4">
                  <div className="rounded-lg border border-koshien-gold/40 bg-[#0F1419]/80 p-4">
                    <div className="mb-2 font-vintage text-[10px] uppercase tracking-widest text-[#A89968] sm:text-xs">
                      {t('game.rival_leave_mound')}
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex-1">
                        <p className="truncate font-vintage text-sm font-bold text-koshien-chalk sm:text-base">
                          {oldPitcher.name}
                        </p>
                        <p className="text-[10px] text-[#A89968] sm:text-xs">
                          #{oldPitcher.number} • {oldPitcher.position}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="font-sports text-lg font-bold text-koshien-gold sm:text-2xl">
                          {oldPitcher.overall}
                        </div>
                        <div className="font-vintage text-[8px] text-[#A89968] sm:text-[9px]">
                          {t('game.intro_ovr')}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 py-1">
                    <div className="h-px flex-1 bg-gradient-to-r from-transparent via-koshien-gold/30 to-transparent" />
                    <div className="px-2 font-vintage text-[10px] uppercase tracking-widest text-[#A89968]">
                      {t('game.rival_relief')}
                    </div>
                    <div className="h-px flex-1 bg-gradient-to-r from-transparent via-koshien-gold/30 to-transparent" />
                  </div>

                  <div className="rounded-lg border border-koshien-gold/60 bg-[#0F1419]/80 p-4 ring-1 ring-koshien-gold/20">
                    <div className="mb-2 font-vintage text-[10px] font-bold uppercase tracking-widest text-koshien-gold sm:text-xs">
                      {t('game.rival_enter_mound')}
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex-1">
                        <p className="truncate font-vintage text-sm font-bold text-koshien-gold sm:text-base">
                          {newPitcher.name}
                        </p>
                        <p className="text-[10px] text-[#A89968] sm:text-xs">
                          #{newPitcher.number} • {newPitcher.position}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="font-sports text-lg font-bold text-koshien-gold sm:text-2xl">
                          {newPitcher.overall}
                        </div>
                        <div className="font-vintage text-[8px] text-[#A89968] sm:text-[9px]">
                          {t('game.intro_ovr')}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mb-6 flex justify-center">
                  <div
                    className="rounded border px-3 py-1 font-vintage text-[10px] font-bold uppercase tracking-wider sm:text-xs"
                    style={{ color: rarityColor(newPitcher.rarity), borderColor: rarityColor(newPitcher.rarity) }}
                  >
                    {newPitcher.rarity}
                  </div>
                </div>

                <motion.button
                  type="button"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={onAccept}
                  className="w-full rounded bg-gradient-to-r from-koshien-gold to-[#D4AF7A] py-2.5 font-vintage text-sm font-bold uppercase tracking-wider text-koshien-dark transition-all duration-200 hover:from-[#D4AF7A] hover:to-[#E8C497] sm:py-3 md:py-3.5 sm:text-base"
                >
                  {t('game.rival_understood')}
                </motion.button>

                <p className="mt-3 text-center font-vintage text-[8px] uppercase tracking-widest text-[#A89968] sm:text-[9px]">
                  {t('game.rival_zero_pitches')}
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    )
  }

  if (availablePitchers && availablePitchers.length > 0) {
    const selectedPitcher = availablePitchers.find((p) => p.id === selectedPitcherId)
    const freshCount = availablePitchers.filter((p) => !p.already_used).length

    const handleConfirm = async () => {
      if (!selectedPitcherId) {
        setError(t('game.select_pitcher_error'))
        return
      }
      if (selectedPitcherId === oldPitcher?.id) {
        setError(t('game.different_pitcher_error'))
        return
      }
      if (!onSelectPitcher) {
        onAccept()
        return
      }
      try {
        setIsSubmitting(true)
        setError(null)
        await onSelectPitcher(selectedPitcherId)
        onAccept()
      } catch {
        setError(t('game.change_error'))
      } finally {
        setIsSubmitting(false)
      }
    }

    return (
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onAccept}
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
                    {t('game.rival_change_title_sel')}
                  </h2>
                  <button
                    type="button"
                    onClick={onAccept}
                    disabled={isLoading || isSubmitting}
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
                      <PitcherMiniCard pitcher={oldPitcher} dimmed />
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
                              title={isUsed ? t('game.your_used') : undefined}
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
                                    isUsed ? 'bg-[#2A2A2A] text-[#555555]' : 'bg-koshien-gold/20 text-koshien-gold'
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
                      onClick={onAccept}
                      disabled={isLoading || isSubmitting}
                      className="rounded-lg border border-koshien-gold/50 px-4 py-2 font-vintage text-sm font-bold text-koshien-gold transition-colors hover:bg-koshien-gold/10 disabled:opacity-50"
                    >
                      {t('game.cancel')}
                    </button>
                    <motion.button
                      type="button"
                      onClick={handleConfirm}
                      disabled={isLoading || isSubmitting || !selectedPitcherId || selectedPitcherId === oldPitcher?.id}
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      className="rounded-lg bg-koshien-gold px-6 py-2 font-vintage text-sm font-bold text-koshien-dark transition-colors hover:bg-koshien-chalk disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {isSubmitting ? (
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

  return null
}

function rarityColor(rarity?: string): string {
  switch (rarity) {
    case 'DIAMOND':
      return '#4A90E2'
    case 'GOLD':
      return '#FFD700'
    case 'SILVER':
      return '#C0C0C0'
    case 'BRONZE':
      return '#CD7F32'
    default:
      return '#A89968'
  }
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