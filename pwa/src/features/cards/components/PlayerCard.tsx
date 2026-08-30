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

export function PlayerCard({ card, selected = false, onSelect, size = 'md' }: Props) {
  const { t } = useTranslation()
  const rarity = card.rarity?.toUpperCase() ?? 'COMMON'
  const isPitcher = card.position === 'SP' || card.position === 'RP' || card.position === 'CP'
  const glow = `card-glow ${RARITY_GLOW[rarity] ?? 'card-glow-common'}`
  const ring = onSelect
    ? `cursor-pointer transition-transform ${selected ? 'scale-[1.03]' : 'hover:scale-[1.02]'}`
    : ''
  const sm = size === 'sm'
  const nameCls = sm ? 'text-xs' : 'text-base'
  const metaCls = sm ? 'text-[7px]' : 'text-[9px]'
  const ovrCls = sm ? 'text-sm' : 'text-xl'
  const ovrLabelCls = sm ? 'text-[6px]' : 'text-[8px]'
  const badgeCls = sm ? 'text-[7px]' : 'text-[9px]'
  const statValueCls = sm ? 'text-[10px]' : 'text-sm'
  const padding = sm ? 'p-2' : 'p-3'
  const gap = sm ? 'gap-1.5' : 'gap-2.5'

  return (
    <div
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      aria-pressed={onSelect ? selected : undefined}
      onClick={onSelect}
      onKeyDown={onSelect ? (e) => e.key === 'Enter' && onSelect() : undefined}
      className={`${glow} ${ring} aspect-[3/4]`}
    >
      <div className={`card-glow-inner flex h-full w-full flex-col ${gap} bg-koshien-dark ${padding}`}>
        <header className="flex items-start justify-between gap-1">
          <div className="flex flex-col">
            <span className={`font-sports ${nameCls} font-bold uppercase leading-none text-koshien-chalk`}>
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
              <span className={`rounded-full border border-koshien-gold/40 px-2 py-0.5 font-vintage ${badgeCls} uppercase tracking-widest text-koshien-gold`}>
                {RARITY_LABEL[rarity] ?? rarity}
              </span>
              <span className={`font-vintage ${badgeCls} uppercase tracking-widest text-koshien-cream/70`}>
                {isPitcher ? t('card.pitcher') : t('card.batter')}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-1">
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
    <div className="rounded-lg border border-koshien-border bg-koshien-green/40 px-1.5 py-1">
      <div className="flex items-baseline justify-between">
        <span className="font-vintage text-[9px] uppercase text-koshien-cream/60">{label}</span>
        <span className={`font-sports ${valueCls} font-bold text-koshien-chalk`}>{value}</span>
      </div>
    </div>
  )
}
