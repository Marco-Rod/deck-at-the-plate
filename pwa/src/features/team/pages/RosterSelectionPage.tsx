import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useAuthStore, selectUser } from '@/features/auth/store'
import { useRosterStore, selectInventory } from '@/features/team/rosterStore'
import { useLobbyStore } from '@/features/lobby/store'
import { createGame } from '@/features/lobby/api'
import { bestCardFor, findCard, findFreeSpot } from '@/features/team/lib/cardHelpers'
import { Button, Spinner } from '@/shared/ui'
import type { PlayerCard as PlayerCardData } from '@/shared/api/types'

const BATTING_SPOTS = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

export function RosterSelectionPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const user = useAuthStore(selectUser)
  const inventory = useRosterStore(selectInventory)
  const { load, hasLoaded, loading } = useRosterStore()
  const config = useLobbyStore((s) => s.config)

  const [lineup, setLineup] = useState<Record<string, string>>({})
  const [selectedPitcherId, setSelectedPitcherId] = useState<string | null>(null)
  const [deck] = useState<string[]>(['t1', 't2', 't3', 't4', 't1'])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void load()
  }, [load])

  const batters = useMemo(
    () =>
      (inventory ?? [])
        .filter((i) => i.card.position !== 'SP' && i.card.position !== 'RP')
        .sort((a, b) => b.card.overall - a.card.overall),
    [inventory],
  )

  const pitchers = useMemo(
    () =>
      (inventory ?? [])
        .filter((i) => i.card.position === 'SP' || i.card.position === 'RP')
        .sort((a, b) => b.card.overall - a.card.overall),
    [inventory],
  )

  // Auto-seleccionar el primer pitcher si no hay seleccionado
  useEffect(() => {
    if (!selectedPitcherId && pitchers.length > 0) {
      const firstPitcher = pitchers[0]
      if (firstPitcher) {
        setSelectedPitcherId(firstPitcher.card.id)
      }
    }
  }, [pitchers, selectedPitcherId])

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

  const autoAssignLineup = () => {
    const assigned: Record<string, string> = {}
    const usedCardIds = new Set<string>()

    // Asignar bateadores por posición (1-9 del batting order)
    for (const spot of BATTING_SPOTS) {
      const match = bestCardFor(
        batters,
        (c) => !usedCardIds.has(c.id),
      )
      if (match) {
        assigned[spot] = match.id
        usedCardIds.add(match.id)
      }
    }

    // Asignar el mejor pitcher disponible
    const pitcher = bestCardFor(
      pitchers,
      (c) => !usedCardIds.has(c.id),
    )
    if (pitcher) {
      setSelectedPitcherId(pitcher.id)
    }

    setLineup(assigned)
  }

  const handleConfirm = async () => {
    if (!user) return

    if (!config.rivalId) {
      setError(t('roster.error_no_rival'))
      return
    }

    const filledSlots = Object.values(lineup).filter(Boolean)
    if (filledSlots.length === 0) {
      setError(t('roster.error_empty'))
      return
    }

    if (!selectedPitcherId && pitchers.length > 0) {
      setError('Debes seleccionar un pitcher')
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      const homeLineup: string[] = Object.keys(lineup)
        .sort((a, b) => Number(a) - Number(b))
        .map((spot) => lineup[spot])
        .filter((id): id is string => Boolean(id))

      const payload = {
        home_user_id: user.userId,
        away_user_id: config.rivalId,
        game_mode: config.gameMode,
        difficulty: config.difficulty,
        total_innings: config.innings,
        player_position: config.playerPosition,
        home_pitcher_id: selectedPitcherId || undefined,
        home_lineup: homeLineup,
        home_tactics_deck: deck,
      }

      const game = await createGame(payload)
      navigate(`/game/${game.id}`)
    } catch (error) {
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
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-sports text-xl font-bold uppercase tracking-wide text-koshien-chalk">
            {t('roster.pick_lineup')}
          </h2>
          <Button
            size="sm"
            onClick={autoAssignLineup}
            className="border border-koshien-gold bg-koshien-green text-koshien-gold hover:bg-koshien-light-green"
          >
            {t('team.auto_lineup') || 'Auto Alinear'}
          </Button>
        </div>
        <div className="space-y-2">
          {batters.map((item) => {
            const inLineup = Object.values(lineup).includes(item.card.id)
            const spot = Object.entries(lineup).find(([_, id]) => id === item.card.id)?.[0]
            return (
              <button
                key={item.inventory_id}
                onClick={() => {
                  if (inLineup && spot) {
                    const next = { ...lineup }
                    delete next[spot]
                    setLineup(next)
                  } else {
                    const freeSpot = findFreeSpot(lineup, BATTING_SPOTS)
                    if (freeSpot) assign(freeSpot, item.card)
                  }
                }}
                className={`w-full rounded-lg border-2 px-4 py-3 text-left transition-colors ${
                  inLineup
                    ? 'border-koshien-gold bg-koshien-gold/20'
                    : 'border-koshien-border bg-koshien-dark/60 hover:border-koshien-gold/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-sports text-sm font-bold text-koshien-chalk">{item.card.name}</div>
                    <div className="font-vintage text-xs text-koshien-cream/60">
                      {item.card.team_id} • {item.card.position} • #{item.card.number}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="font-sports text-sm font-bold text-koshien-gold">{item.card.overall}</div>
                      <div className="font-vintage text-xs text-koshien-cream/60">OVR</div>
                    </div>
                    {inLineup && (
                      <div className="rounded-lg bg-koshien-gold/30 px-2 py-1">
                        <div className="font-sports text-xs font-bold text-koshien-gold">SPOT {spot}</div>
                      </div>
                    )}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </section>

      {pitchers.length > 0 ? (
        <section className="mb-8">
          <h2 className="mb-3 font-sports text-xl font-bold uppercase tracking-wide text-koshien-chalk">
            {t('roster.pitcher') || 'Pitcher'}
          </h2>
          <p className="mb-3 font-vintage text-xs uppercase tracking-widest text-koshien-cream/60">
            Selecciona tu lanzador titular {selectedPitcherId ? '(seleccionado)' : ''}
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {pitchers.map((item) => {
              const isSelected = selectedPitcherId === item.card.id
              return (
                <button
                  key={item.inventory_id}
                  onClick={() => setSelectedPitcherId(item.card.id)}
                  className={`rounded-lg border-2 p-3 text-center transition-colors ${
                    isSelected
                      ? 'border-koshien-gold bg-koshien-gold/20'
                      : 'border-koshien-border bg-koshien-dark/60 hover:border-koshien-gold/50'
                  }`}
                >
                  <div className="font-sports text-sm font-bold text-koshien-chalk">{item.card.name}</div>
                  <div className="font-vintage text-xs text-koshien-cream/60">{item.card.position}</div>
                  <div className="font-sports text-xs text-koshien-gold">{item.card.overall} OVR</div>
                </button>
              )
            })}
          </div>
        </section>
      ) : (
        <section className="mb-8">
          <h2 className="mb-3 font-sports text-xl font-bold uppercase tracking-wide text-koshien-chalk">
            {t('roster.pitcher') || 'Pitcher'}
          </h2>
          <div className="rounded-lg border border-koshien-border bg-koshien-dark/60 p-4 text-center">
            <p className="font-vintage text-xs uppercase text-koshien-cream/60">
              No tienes lanzadores en tu inventario. Ve a "Mi Equipo" para adquirir uno.
            </p>
          </div>
        </section>
      )}



      {error ? (
        <p className="mb-3 font-vintage text-xs uppercase text-red-400">{error}</p>
      ) : null}

      <Button size="lg" disabled={submitting || !config.rivalId} onClick={handleConfirm}>
        {submitting ? t('roster.creating') : t('roster.start')}
      </Button>
    </motion.div>
  )
}
