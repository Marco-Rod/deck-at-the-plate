import { useTranslation } from 'react-i18next'
import type { PlayerCard as PlayerCardData } from '@/shared/api/types'

const RARITY_LABEL: Record<string, string> = {
  COMMON: 'COMÚN',
  BRONZE: 'BRONCE',
  SILVER: 'PLATA',
  GOLD: 'ORO',
  DIAMOND: 'DIAMANTE',
}

const RARITY_GLOW: Record<string, string> = {
  COMMON: 'card-glow-common',
  BRONZE: 'card-glow-bronze',
  SILVER: 'card-glow-silver',
  GOLD: 'card-glow-gold',
  DIAMOND: 'card-glow-diamond',
}

interface Props {
  card: PlayerCardData
  selected?: boolean
  onSelect?: () => void
  size?: 'sm' | 'md'
}

export function PlayerCardShowcase({ card, selected = false, onSelect, size = 'md' }: Props) {
  const { t } = useTranslation()
  const rarity = card.rarity?.toUpperCase() ?? 'COMMON'
  const isPitcher = card.position === 'SP' || card.position === 'RP' || card.position === 'CP'
  const glow = `card-glow ${RARITY_GLOW[rarity] ?? 'card-glow-common'}`
  const ring = onSelect
    ? `cursor-pointer transition-transform ${selected ? 'scale-[1.03]' : 'hover:scale-[1.02]'}`
    : ''
  const sm = size === 'sm'
  const nameCls = sm ? 'text-xs' : 'text-xl sm:text-2xl'
  const metaCls = sm ? 'text-[7px]' : 'text-[11px] sm:text-xs'
  const ovrCls = sm ? 'text-sm' : 'text-3xl sm:text-4xl'
  const ovrLabelCls = sm ? 'text-[6px]' : 'text-[9px] sm:text-[10px]'
  const badgeCls = sm ? 'text-[7px]' : 'text-[11px] sm:text-xs'
  const statValueCls = sm ? 'text-[10px]' : 'text-xl sm:text-2xl'
  const padding = sm ? 'p-1.5' : 'p-4 sm:p-5'
  const gap = sm ? 'gap-1' : 'gap-3 sm:gap-4'
  const aspectRatio = 'aspect-[5/7]'

  return (
    <div
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      aria-pressed={onSelect ? selected : undefined}
      onClick={onSelect}
      onKeyDown={onSelect ? (e) => e.key === 'Enter' && onSelect() : undefined}
      className={`${glow} ${ring} ${aspectRatio}`}
    >
      <div className={`card-glow-inner flex h-full w-full flex-col ${gap} bg-koshien-dark ${padding}`}>
        <header className="flex items-start justify-between gap-1">
          <div className="min-w-0 flex-1">
            <span className={`block font-sports ${nameCls} font-bold uppercase leading-tight text-koshien-chalk`}>
              {card.name}
            </span>
            <span className={`mt-0.5 font-vintage ${metaCls} uppercase tracking-widest text-koshien-cream/70`}>
              {card.team_id ?? '—'} • {card.position} • #{card.number}
            </span>
          </div>
          <div className="flex flex-col items-center rounded-lg border border-koshien-border bg-koshien-green/50 px-1 py-0.5">
            <span className={`font-sports ${ovrCls} font-bold leading-none text-koshien-gold`}>
              {card.overall}
            </span>
            <span className={`font-vintage ${ovrLabelCls} uppercase text-koshien-cream/60`}>OVR</span>
          </div>
        </header>

        {!sm && (
          <>
            <div className="flex flex-wrap items-center gap-1">
              <span className={`showcase-rarity-badge rounded-full border px-2 py-0.5 font-vintage ${badgeCls} uppercase tracking-widest`}>
                {RARITY_LABEL[rarity] ?? rarity}
              </span>
              <span className={`font-vintage ${badgeCls} uppercase tracking-widest text-koshien-cream/70`}>
                {isPitcher ? t('card.pitcher') : t('card.batter')}
              </span>
            </div>

            <div className="showcase-player-identity" aria-hidden="true">
              <span className="showcase-player-position font-vintage uppercase">{card.position}</span>
              <span className="showcase-player-number font-sports font-bold">#{card.number}</span>
            </div>

            <div className="mt-auto grid grid-cols-2 gap-2 sm:gap-3">
              <Stat label={t('card.power')} value={card.power} valueCls={statValueCls} />
              <Stat label={t('card.contact')} value={card.contact} valueCls={statValueCls} />
              {isPitcher || card.is_two_way ? (
                <>
                  <Stat label={t('card.velocity')} value={card.velocity} valueCls={statValueCls} />
                  <Stat label={t('card.control')} value={card.control} valueCls={statValueCls} />
                </>
              ) : null}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value, valueCls = 'text-sm' }: { label: string; value: number; valueCls?: string }) {
  return (
    <div className="rounded-lg border border-koshien-border bg-koshien-green/40 px-2 py-2 sm:px-3 sm:py-2.5">
      <div className="flex items-baseline justify-between">
        <span className="font-vintage text-[10px] uppercase text-koshien-cream/60 sm:text-xs">{label}</span>
        <span className={`font-sports ${valueCls} font-bold text-koshien-chalk`}>{value}</span>
      </div>
    </div>
  )
}
