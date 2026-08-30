import { useTranslation } from 'react-i18next'
import type { PlayerRole, TacticalCard } from '@/shared/api/types'
import { SubmitPlayButton } from './SubmitPlayButton'
import { TacticalCardItem } from './TacticalCardItem'

interface TacticalHandProps {
  tacticalHand: TacticalCard[]
  selectedTacticalId: string | null
  role: PlayerRole
  isIBB: boolean
  disabled: boolean
  onSelectTactical: (id: string) => void
  onSubmitPlay: () => void
}

export function TacticalHand({
  tacticalHand,
  selectedTacticalId,
  role,
  isIBB,
  disabled = false,
  onSelectTactical,
  onSubmitPlay,
}: TacticalHandProps) {
  const { t } = useTranslation()

  const buttonLabel = isIBB
    ? t('game.tactic_intentional')
    : role === 'PITCHER'
      ? t('game.tactic_pitch')
      : t('game.tactic_bat')

  return (
    <footer className="mx-auto mt-3 flex w-full max-w-6xl flex-col items-center justify-between gap-4 border border-koshien-gold/60 bg-koshien-dark p-3.5 shadow-2xl md:flex-row">
      <div className="flex flex-col">
        <span className="font-vintage text-xs font-bold uppercase text-koshien-gold">
          {t('game.tactical_hand_title')}
        </span>
        <span className="font-vintage text-[10px] text-koshien-cream/70">
          {t('game.tactical_hand_subtitle')}
        </span>
      </div>

      <div className="flex gap-3 overflow-x-auto py-1">
        {tacticalHand.map((card) => (
          <TacticalCardItem
            key={card.id}
            card={card}
            isSelected={selectedTacticalId === card.id}
            disabled={disabled}
            onSelect={onSelectTactical}
          />
        ))}
      </div>

      <SubmitPlayButton label={buttonLabel} disabled={disabled} onSubmit={onSubmitPlay} />
    </footer>
  )
}