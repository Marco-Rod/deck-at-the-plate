import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useRosterStore, selectInventory } from '@/features/team/rosterStore'
import { PlayerCardShowcase } from '@/features/cards/components/PlayerCardShowcase'
import { Spinner } from '@/shared/ui'

const FILTERS = ['ALL', 'SP', 'RP', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']

export function CardShowcasePage() {
  const { t } = useTranslation()
  const inventory = useRosterStore(selectInventory)
  const { load, hasLoaded, loading } = useRosterStore()
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    void load()
  }, [load])

  const cards = useMemo(() => {
    const list = inventory ?? []
    if (filter === 'ALL') return list
    return list.filter((i) => i.card.position === filter)
  }, [inventory, filter])

  if (!hasLoaded || loading) {
    return <Spinner label={t('common.loading')} className="min-h-screen py-20" />
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto min-h-screen w-full max-w-2xl px-4 py-6 sm:px-6"
    >
      <h1 className="mb-1 font-sports text-3xl font-bold uppercase tracking-wide text-koshien-gold">
        {t('showcase.title')}
      </h1>
      <p className="mb-6 font-vintage text-xs uppercase tracking-widest text-koshien-cream/60">
        {t('showcase.subtitle')}
      </p>

      <div className="mb-6 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={`rounded-full border px-3 py-1 font-sports uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
              filter === f
                ? 'border-koshien-gold bg-koshien-gold text-koshien-dark'
                : 'border-koshien-border bg-koshien-green text-koshien-cream hover:border-koshien-gold/50'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {cards.length === 0 ? (
        <p className="font-vintage text-xs uppercase tracking-widest text-koshien-cream/60">
          {t('showcase.empty')}
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {cards.map((item) => (
            <PlayerCardShowcase key={item.inventory_id} card={item.card} size="md" />
          ))}
        </div>
      )}
    </motion.div>
  )
}
