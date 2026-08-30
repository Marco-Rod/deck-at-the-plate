import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useAuthStore, selectUser } from '@/features/auth/store'
import { useRosterStore, selectInventory } from '@/features/team/rosterStore'
import { useLobbyStore } from '@/features/lobby/store'
import { createGame } from '@/features/lobby/api'
import { PlayerCard } from '@/features/cards/components/PlayerCard'
import { Button, Spinner } from '@/shared/ui'
import type { PlayerCard as PlayerCardData } from '@/shared/api/types'

const BATTING_SPOTS = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

const TACTIC_OPTIONS: { id: string; name: string; desc: string }[] = [
  { id: 't1', name: 'Paciencia en el Plato', desc: '+Visión' },
  { id: 't2', name: 'Swing de Barril', desc: '+Poder' },
  { id: 't3', name: 'Batazo de Contacto', desc: '+Contacto' },
  { id: 't4', name: 'Recta de Fuego', desc: '+Velocidad' },
]

export function RosterSelectionPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { gameId } = useParams<{ gameId: string }>()
  const user = useAuthStore(selectUser)
  const inventory = useRosterStore(selectInventory)
  const { load, hasLoaded, loading } = useRosterStore()
  const config = useLobbyStore((s) => s.config)

  const [lineup, setLineup] = useState<Record<string, string>>({})
  const [deck, setDeck] = useState<string[]>(['t1', 't2', 't3', 't4', 't1'])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void load()
  }, [load])

  const batters = useMemo(
    () => (inventory ?? []).filter((i) => i.card.position !== 'SP' && i.card.position !== 'RP'),
    [inventory],
  )

  if (!hasLoaded || loading) {
    return <Spinner label={t('common.loading')} className="min-h-screen py-20" />
  }

  const assign = (slot: string, card: PlayerCardData) => {
    setLineup((prev) => {
      const next = { ...prev }
      // remove card from other slot if already assigned
      for (const [s, c] of Object.entries(next)) {
        if (c === card.id) delete next[s]
      }
      next[slot] = card.id
      return next
    })
  }

  const toggleDeckCard = (id: string) => {
    setDeck((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const handleConfirm = async () => {
    if (!user) return
    const filledSlots = Object.values(lineup).filter(Boolean)
    if (filledSlots.length === 0) {
      setError(t('roster.error_empty'))
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const homeLineup: string[] = Object.keys(lineup)
        .sort((a, b) => Number(a) - Number(b))
        .map((spot) => lineup[spot])
        .filter((id): id is string => Boolean(id))
      const game = await createGame({
        home_user_id: user.userId,
        away_user_id: 'CPU_BOT',
        game_mode: 'PVE',
        difficulty: config.difficulty,
        total_innings: config.innings,
        player_position: 'HOME',
        home_lineup: homeLineup,
        home_tactics_deck: deck,
      })
      if (gameId && game.id !== gameId) {
        navigate(`/game/${game.id}`, { replace: true })
      } else {
        navigate(`/game/${game.id}`)
      }
    } catch {
      setError(t('roster.error_generic'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto min-h-screen w-full max-w-2xl px-4 py-6 sm:px-6"
    >
      <h1 className="mb-1 font-sports text-3xl font-bold uppercase tracking-wide text-koshien-gold">
        {t('roster.title')}
      </h1>
      <p className="mb-6 font-vintage text-xs uppercase tracking-widest text-koshien-cream/60">
        {t('roster.subtitle')}
      </p>

      <section className="mb-8">
        <h2 className="mb-3 font-sports text-xl font-bold uppercase tracking-wide text-koshien-chalk">
          {t('roster.lineup')}
        </h2>
        <div className="rounded-xl border border-koshien-border bg-koshien-dark/80 p-4">
          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-3">
            {BATTING_SPOTS.map((spot) => {
              const assigned = findCard(batters, lineup[spot])
              return (
                <button
                  key={spot}
                  type="button"
                  onClick={() => assigned && assign(spot, assigned)}
                  disabled={!assigned}
                  className={`flex items-center justify-between rounded-lg px-3 py-2 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
                    assigned
                      ? 'bg-koshien-green/60 hover:bg-koshien-light-green'
                      : 'bg-koshien-green/20 text-koshien-cream/40'
                  }`}
                  title={assigned ? t('roster.remove') : undefined}
                >
                  <span className="font-sports text-sm font-bold text-koshien-gold">{spot}</span>
                  <span className="font-sports text-sm font-bold uppercase text-koshien-chalk">
                    {assigned ? assigned.name : t('roster.empty')}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 font-sports text-xl font-bold uppercase tracking-wide text-koshien-chalk">
          {t('roster.pick_lineup')}
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {batters.map((item) => {
            const inLineup = Object.values(lineup).includes(item.card.id)
            return (
              <PlayerCard
                key={item.inventory_id}
                card={item.card}
                selected={inLineup}
                onSelect={() => {
                  const spot = findFreeSpot(lineup, BATTING_SPOTS)
                  if (spot) assign(spot, item.card)
                }}
                size="sm"
              />
            )
          })}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 font-sports text-xl font-bold uppercase tracking-wide text-koshien-chalk">
          {t('roster.deck')}
        </h2>
        <p className="mb-3 font-vintage text-xs uppercase tracking-widest text-koshien-cream/60">
          {t('roster.deck_hint')}
        </p>
        <div className="flex flex-wrap gap-2">
          {TACTIC_OPTIONS.map((tac) => {
            const active = deck.includes(tac.id)
            return (
              <button
                key={tac.id}
                type="button"
                onClick={() => toggleDeckCard(tac.id)}
                aria-pressed={active}
                className={`rounded-lg border px-4 py-2 font-sports uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
                  active
                    ? 'border-koshien-gold bg-koshien-gold text-koshien-dark'
                    : 'border-koshien-border bg-koshien-green text-koshien-cream hover:border-koshien-gold/50'
                }`}
              >
                <span className="block text-base font-bold">{tac.name}</span>
                <span className="block font-vintage text-[10px] tracking-widest">{tac.desc}</span>
              </button>
            )
          })}
        </div>
      </section>

      {error ? (
        <p className="mb-3 font-vintage text-xs uppercase text-red-400">{error}</p>
      ) : null}

      <Button size="lg" disabled={submitting} onClick={handleConfirm}>
        {submitting ? t('roster.creating') : t('roster.start')}
      </Button>
    </motion.div>
  )
}

function findCard(list: { card: PlayerCardData }[], id?: string) {
  if (!id) return undefined
  return list.find((i) => i.card.id === id)?.card
}

function findFreeSpot(lineup: Record<string, string>, spots: string[]): string | undefined {
  return spots.find((s) => !lineup[s])
}
