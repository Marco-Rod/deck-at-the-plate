import { useTranslation } from 'react-i18next'
import type { PlayerCard as PlayerCardData } from '@/shared/api/types'

const RARITY_LABEL: Record<string, string> = {
  COMMON: 'COMÚN',
  BRONZE: 'BRONCE',
  SILVER: 'PLATA',
  GOLD: 'ORO',
  DIAMOND: 'DIAMANTE',
}

export function PlayerCardFront({ card }: { card: PlayerCardData }) {
  const { t } = useTranslation()
  const rarity = (card.rarity?.toUpperCase() ?? 'COMMON') as string
  const isPitcher = card.position === 'SP' || card.position === 'RP' || card.position === 'CP'
  const isTwoWay = Boolean(card.is_two_way)
  const showPitch = isPitcher || isTwoWay

  return (
    <div className="flex h-full w-full flex-col">
      <header className="card-front-header">
        <div className="min-w-0">
          <span className="card-front-name block font-sports text-sm font-bold uppercase leading-none text-koshien-chalk sm:text-base">
            {card.name}
          </span>
          <span className="mt-0.5 block font-vintage text-[9px] uppercase tracking-widest text-koshien-cream/70">
            {card.team_id ?? '—'} · {card.position} · #{card.number}
          </span>
        </div>
        <div className="card-ovr-badge">
          <span className="card-ovr-value font-sports leading-none text-koshien-gold">
            {card.overall}
          </span>
          <span className="card-ovr-label font-vintage uppercase text-koshien-cream/60">OVR</span>
        </div>
      </header>

      <div className="mt-1 flex items-center gap-1.5">
        <span className="rarity-badge font-vintage uppercase">
          {RARITY_LABEL[rarity] ?? rarity}
        </span>
        <span className="font-vintage text-[9px] uppercase tracking-[0.1em] text-koshien-cream/70">
          {t(isPitcher ? 'card.pitcher' : 'card.batter')}
        </span>
      </div>

      <div className="card-player-identity">
        <span className="card-player-name font-sports font-bold text-koshien-chalk">
          {card.name}
        </span>
        <span className="card-player-number font-sports text-koshien-chalk">{card.number}</span>
      </div>

      <div className="card-stats">
        <CardStat label={t('card.power')} value={card.power} />
        <CardStat label={t('card.contact')} value={card.contact} />
        {showPitch ? (
          <>
            <CardStat label={t('card.velocity')} value={card.velocity} />
            <CardStat label={t('card.control')} value={card.control} />
          </>
        ) : null}
      </div>

      <span className="sr-only">
        {RARITY_LABEL[rarity] ?? rarity} · OVR {card.overall}
      </span>
    </div>
  )
}

function CardStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="card-stat">
      <span className="card-stat__label font-vintage uppercase tracking-widest text-koshien-cream/60">
        {label}
      </span>
      <span className="card-stat__value font-sports font-bold text-koshien-chalk">{value}</span>
    </div>
  )
}
