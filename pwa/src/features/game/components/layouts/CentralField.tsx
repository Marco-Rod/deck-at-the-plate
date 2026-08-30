import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { GameRunners, PitchAttribute, PlayerGameData, PlayerRole } from '@/shared/api/types'
import { changePitcher, getAvailablePitchers } from '@/features/game/api'
import { GameInfo } from '../base'
import { PitchZoneGrid } from '../pitch'
import { PlayerCard } from '../PlayerCard'
import { ChangePitcherModal } from '../modals/ChangePitcherModal'

const EMPTY_RUNNERS: GameRunners = { b1: null, b2: null, b3: null }
const MIN_PITCHES_TO_CHANGE = 5

interface InningTransitionView {
  visible: boolean
}

interface CentralFieldProps {
  role: PlayerRole
  pitcherCard: PlayerGameData | null
  batterCard: PlayerGameData | null
  selectedZone: number
  selectedPitch: string
  repertoire?: PitchAttribute[]
  hasPitched: boolean
  isAwaitingResult: boolean
  inningTransition?: InningTransitionView | null
  onSelectZone: (zone: number) => void
  onSelectPitch: (pitch: string) => void
  balls?: number
  strikes?: number
  outs?: number
  currentInning?: number
  totalInnings?: number
  isTopInning?: boolean
  runners?: GameRunners
  gameId?: string | null
  fatigueLevel?: number
  pitchCount?: number
  onPitcherChanged?: (newPitcher: PlayerGameData) => void
}

interface BullpenPitcher extends PlayerGameData {
  already_used?: boolean
}

export function CentralField({
  role,
  pitcherCard,
  batterCard,
  selectedZone,
  selectedPitch,
  repertoire,
  hasPitched,
  isAwaitingResult,
  inningTransition,
  onSelectZone,
  onSelectPitch,
  balls = 0,
  strikes = 0,
  outs = 0,
  currentInning = 1,
  totalInnings = 9,
  isTopInning = true,
  runners = EMPTY_RUNNERS,
  gameId,
  fatigueLevel = 0,
  pitchCount = 0,
  onPitcherChanged,
}: CentralFieldProps) {
  const { t } = useTranslation()
  const [showChangePitcherModal, setShowChangePitcherModal] = useState(false)
  const [availablePitchers, setAvailablePitchers] = useState<BullpenPitcher[]>([])
  const [isLoadingPitchers, setIsLoadingPitchers] = useState(false)
  const [showMinPitchesHint, setShowMinPitchesHint] = useState(false)

  const canChangePitcher = pitchCount >= MIN_PITCHES_TO_CHANGE

  const loadAvailablePitchers = async () => {
    if (!gameId) return
    try {
      setIsLoadingPitchers(true)
      const response = await getAvailablePitchers(gameId)
      setAvailablePitchers(response.available_pitchers || [])
    } catch {
      setAvailablePitchers([])
    } finally {
      setIsLoadingPitchers(false)
    }
  }

  const handleClickPitcherCard = () => {
    if (!canChangePitcher) {
      setShowMinPitchesHint(true)
      window.setTimeout(() => setShowMinPitchesHint(false), 2000)
      return
    }
    setShowChangePitcherModal(true)
    void loadAvailablePitchers()
  }

  const handleChangePitcher = async (newPitcherId: string) => {
    if (!gameId) return
    const response = await changePitcher(gameId, {
      new_pitcher_id: newPitcherId,
      player_role: 'PITCHER',
    })
    if (response.active_pitcher && onPitcherChanged) {
      onPitcherChanged(response.active_pitcher)
    }
  }

  return (
    <div className="relative z-10 flex w-full flex-col items-center gap-1 px-0.5 sm:gap-2 sm:px-1 md:gap-3 md:px-2 lg:gap-6">
      <div className="flex w-full justify-center px-0.5 sm:px-1">
        <div className="w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-2xl">
          <GameInfo
            balls={balls}
            strikes={strikes}
            outs={outs}
            currentInning={currentInning}
            totalInnings={totalInnings}
            isTopInning={isTopInning}
            runners={runners}
          />
        </div>
      </div>

      <div className="flex w-full flex-col flex-wrap items-center justify-center gap-1 sm:flex-row sm:gap-2 md:gap-4 lg:gap-6">
        <div className="flex w-24 flex-shrink-0 items-start justify-center sm:w-32 md:w-40 lg:w-56">
          <div className="relative">
            <PlayerCard
              player={pitcherCard}
              role="PITCHER"
              disablePulse={true}
              size="sm"
              fatigueLevel={fatigueLevel}
              onClickPitcher={role === 'PITCHER' ? handleClickPitcherCard : undefined}
            />

            {role === 'PITCHER' && !canChangePitcher && pitchCount > 0 && (
              <div className="pointer-events-none absolute -bottom-5 left-0 right-0 flex justify-center">
                <span className="whitespace-nowrap font-vintage text-[9px] text-[#A89968]/70">
                  {t('game.pitches_to_change', { count: MIN_PITCHES_TO_CHANGE - pitchCount })}
                </span>
              </div>
            )}

            {showMinPitchesHint && (
              <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
                <div className="rounded-lg border border-koshien-gold/60 bg-[#0F1419]/95 px-2 py-1.5 text-center shadow-lg">
                  <p className="font-vintage text-[10px] font-bold leading-tight text-koshien-gold">
                    {t('game.min_pitches', { count: MIN_PITCHES_TO_CHANGE })}
                  </p>
                  <p className="font-vintage text-[9px] leading-tight text-[#A89968]">
                    {t('game.missing_pitches', { count: MIN_PITCHES_TO_CHANGE - pitchCount })}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="w-full flex-shrink-0 sm:w-auto">
          <PitchZoneGrid
            role={role}
            selectedZone={selectedZone}
            selectedPitch={selectedPitch}
            onSelectZone={onSelectZone}
            onSelectPitch={onSelectPitch}
            repertoire={repertoire}
            disabled={isAwaitingResult || !!inningTransition?.visible}
          />
        </div>

        <div className="flex w-24 flex-shrink-0 items-start justify-center sm:w-32 md:w-40 lg:w-56">
          <PlayerCard player={batterCard} role="BATTER" disablePulse={true} size="sm" />
        </div>
      </div>

      {hasPitched && role === 'BATTER' && (
        <div className="z-20 mt-1 animate-bounce rounded-sm bg-koshien-gold/90 px-3 py-1 text-center font-vintage text-[10px] font-bold text-koshien-dark shadow-lg sm:mt-2 sm:px-4 sm:py-2 sm:text-xs md:px-6 md:text-sm">
          {t('game.la_picho')}
        </div>
      )}

      <ChangePitcherModal
        isOpen={showChangePitcherModal}
        onClose={() => setShowChangePitcherModal(false)}
        currentPitcher={pitcherCard}
        availablePitchers={availablePitchers}
        onConfirm={handleChangePitcher}
        isLoading={isLoadingPitchers}
      />
    </div>
  )
}