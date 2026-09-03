import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { PlayerCard as PlayerCardData } from '@/shared/api/types'
import { CardBack } from './PlayerCardBack'
import { PlayerCardFront } from './PlayerCardFront'

const RARITY_ANTICIPATION: Record<string, number> = {
  COMMON: 100,
  BRONZE: 150,
  SILVER: 190,
  GOLD: 260,
  DIAMOND: 420,
}

interface Props {
  card: PlayerCardData
  revealed: boolean
  onReveal: () => void
  revealAll?: boolean
  index?: number
}

export function PlayerCardReveal({ card, revealed, onReveal, revealAll = false, index = 0 }: Props) {
  const { t } = useTranslation()
  const rarity = (card.rarity?.toUpperCase() ?? 'COMMON') as string
  const [isRevealing, setIsRevealing] = useState(false)
  const [revealedState, setRevealedState] = useState(false)
  const [complete, setComplete] = useState(false)
  const started = useRef(false)

  useEffect(() => {
    if (!revealed || started.current) return
    started.current = true

    const anticipation = RARITY_ANTICIPATION[rarity] ?? 100
    const start = revealAll ? index * 130 : 0

    const timers: number[] = []
    timers.push(
      window.setTimeout(() => setIsRevealing(true), start),
      window.setTimeout(() => setRevealedState(true), start + anticipation),
      window.setTimeout(() => {
        setIsRevealing(false)
        setComplete(true)
      }, start + anticipation + 760),
    )

    return () => timers.forEach(window.clearTimeout)
  }, [revealed, rarity, revealAll, index])

  const handleClick = () => {
    if (!revealed) onReveal()
  }

  const classes = [
    'pack-card',
    `rarity-${rarity.toLowerCase()}`,
    revealedState ? 'is-revealed' : '',
    isRevealing ? 'is-revealing' : '',
    complete ? 'reveal-complete' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button
      type="button"
      className={classes}
      onClick={handleClick}
      aria-label={revealedState ? undefined : t('card.tapToReveal')}
      aria-expanded={revealedState}
    >
      <div className="pack-card__inner">
        <div className="pack-card__face pack-card__back">
          <CardBack />
        </div>
        <div className="pack-card__face pack-card__front">
          <PlayerCardFront card={card} />
        </div>
      </div>
    </button>
  )
}
