import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useDialogFocus } from '@/shared/ui/useDialogFocus'

interface GameOverModalProps {
  winnerMessage?: string
  homeScore: number
  awayScore: number
  homeTeamName: string
  awayTeamName: string
  userRole?: 'HOME' | 'AWAY'
  winningPitcherName?: string
  winningPitcherSO?: number
  onReturnToLobby: () => void
}

export function GameOverModal({
  winnerMessage,
  homeScore,
  awayScore,
  homeTeamName,
  awayTeamName,
  userRole = 'HOME',
  winningPitcherName,
  winningPitcherSO,
  onReturnToLobby,
}: GameOverModalProps) {
  const { t } = useTranslation()
  const userScore = userRole === 'HOME' ? homeScore : awayScore
  const cpuScore = userRole === 'HOME' ? awayScore : homeScore
  const userTeamName = userRole === 'HOME' ? homeTeamName : awayTeamName
  const cpuTeamName = userRole === 'HOME' ? awayTeamName : homeTeamName
  const dialogRef = useRef<HTMLDivElement>(null)
  useDialogFocus({ active: true, containerRef: dialogRef })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="game-over-title"
        tabIndex={-1}
        className="w-full max-w-md border-2 border-koshien-gold bg-[#0A0D0F] p-8 text-center shadow-[0_0_50px_rgba(197,160,89,0.4)] font-vintage"
      >
        <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-koshien-gold">
          {t('game.over_kicker')}
        </span>

        <h2 id="game-over-title" className="mb-4 font-sports text-4xl uppercase tracking-wider text-koshien-chalk">
          {winnerMessage || t('game.over_default_title')}
        </h2>

        <div className="my-6 flex items-center justify-around border border-koshien-border bg-koshien-dark p-4">
          <div className="flex flex-col items-center">
            <span className="mb-1 text-xs text-gray-400">{userTeamName}</span>
            <span className="font-sports text-3xl text-koshien-gold">{userScore}</span>
          </div>
          <span className="font-sports text-2xl text-gray-600">-</span>
          <div className="flex flex-col items-center">
            <span className="mb-1 text-xs text-gray-400">{cpuTeamName}</span>
            <span className="font-sports text-3xl text-koshien-chalk">{cpuScore}</span>
          </div>
        </div>

        {winningPitcherName && (
          <div className="mb-6 border border-koshien-gold/40 bg-koshien-dark p-4">
            <div className="mb-3 text-xs font-bold uppercase tracking-widest text-koshien-gold">
              {t('game.over_winning_pitcher')}
            </div>
            <div className="flex items-center justify-between">
              <span className="font-vintage text-lg text-koshien-chalk">{winningPitcherName}</span>
              <div className="flex flex-col items-center">
                <span className="mb-1 text-xs text-gray-400">{t('game.over_strikeouts')}</span>
                <span className="font-sports text-2xl text-koshien-gold">
                  {winningPitcherSO ?? 0}
                </span>
              </div>
            </div>
          </div>
        )}

        <p className="mb-6 text-xs text-gray-400">{t('game.over_stats_note')}</p>

        <button
          type="button"
          onClick={onReturnToLobby}
          className="w-full cursor-pointer border-2 border-koshien-gold bg-koshien-green py-3 font-sports text-xl uppercase tracking-widest text-koshien-gold shadow-lg transition-all hover:bg-[#2D5A3F] active:scale-95"
        >
          {t('game.over_back_lobby')}
        </button>
      </div>
    </div>
  )
}
