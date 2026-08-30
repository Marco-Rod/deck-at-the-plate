import { motion } from 'framer-motion'
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
  revealed: boolean
  onReveal: () => void
  revealAll?: boolean
  index?: number
}

export function PlayerCardReveal({ card, revealed, onReveal, revealAll = false, index = 0 }: Props) {
  const { t } = useTranslation()
  const rarity = card.rarity?.toUpperCase() ?? 'COMMON'
  const isPitcher = card.position === 'SP' || card.position === 'RP' || card.position === 'CP'
  const glow = `card-glow ${RARITY_GLOW[rarity] ?? 'card-glow-common'}`

  const front = (
    <div className="card-glow-inner flex h-full w-full flex-col gap-3 bg-koshien-dark p-4">
      <header className="flex items-center justify-between gap-2">
        <div className="flex flex-col">
          <span className="font-sports text-lg font-bold uppercase leading-none text-koshien-chalk">
            {card.name}
          </span>
          <span className="mt-0.5 font-vintage text-[10px] uppercase tracking-widest text-koshien-cream/70">
            {card.team_id ?? '—'} • {card.position} • #{card.number}
          </span>
        </div>
        <div className="flex flex-col items-center rounded-lg border border-koshien-border bg-koshien-green/50 px-2 py-1">
          <span className="font-sports text-2xl font-bold leading-none text-koshien-gold">
            {card.overall}
          </span>
          <span className="font-vintage text-[9px] uppercase text-koshien-cream/60">OVR</span>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-koshien-gold/40 px-2 py-0.5 font-vintage text-[10px] uppercase tracking-widest text-koshien-gold">
          {RARITY_LABEL[rarity] ?? rarity}
        </span>
        <span className="font-vintage text-[10px] uppercase tracking-widest text-koshien-cream/70">
          {isPitcher ? t('card.pitcher') : t('card.batter')}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-koshien-border bg-koshien-green/40 px-2 py-1.5">
          <div className="flex items-baseline justify-between">
            <span className="font-vintage text-[10px] uppercase text-koshien-cream/60">
              {t('card.power')}
            </span>
            <span className="font-sports text-base font-bold text-koshien-chalk">{card.power}</span>
          </div>
        </div>
        <div className="rounded-lg border border-koshien-border bg-koshien-green/40 px-2 py-1.5">
          <div className="flex items-baseline justify-between">
            <span className="font-vintage text-[10px] uppercase text-koshien-cream/60">
              {t('card.contact')}
            </span>
            <span className="font-sports text-base font-bold text-koshien-chalk">{card.contact}</span>
          </div>
        </div>
        {isPitcher || card.is_two_way ? (
          <>
            <div className="rounded-lg border border-koshien-border bg-koshien-green/40 px-2 py-1.5">
              <div className="flex items-baseline justify-between">
                <span className="font-vintage text-[10px] uppercase text-koshien-cream/60">
                  {t('card.velocity')}
                </span>
                <span className="font-sports text-base font-bold text-koshien-chalk">
                  {card.velocity}
                </span>
              </div>
            </div>
            <div className="rounded-lg border border-koshien-border bg-koshien-green/40 px-2 py-1.5">
              <div className="flex items-baseline justify-between">
                <span className="font-vintage text-[10px] uppercase text-koshien-cream/60">
                  {t('card.control')}
                </span>
                <span className="font-sports text-base font-bold text-koshien-chalk">
                  {card.control}
                </span>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  )

  const back = (
    <div className="card-glow-inner flex h-full w-full flex-col items-center justify-center gap-3 bg-koshien-green p-4">
      <span className="font-sports text-4xl">⚾</span>
      <span className="font-sports text-lg font-bold uppercase tracking-widest text-koshien-gold">
        Deck at the Plate
      </span>
      <span className="font-vintage text-[10px] uppercase tracking-widest text-koshien-cream/60">
        {t('card.tapToReveal')}
      </span>
    </div>
  )

  return (
    <motion.div
      className={`${glow} aspect-[3/4] h-full cursor-pointer`}
      onClick={onReveal}
      initial={{ rotateY: 0 }}
      animate={{ rotateY: revealed ? 180 : 0 }}
      transition={{ duration: 0.6, ease: 'easeInOut', delay: revealAll ? index * 0.12 : 0 }}
      style={{ perspective: 1200, transformStyle: 'preserve-3d' }}
    >
      <div
        className="absolute inset-0"
        style={{ backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden' }}
      >
        {back}
      </div>
      <div
        className="absolute inset-0"
        style={{ backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
      >
        {front}
      </div>
    </motion.div>
  )
}
