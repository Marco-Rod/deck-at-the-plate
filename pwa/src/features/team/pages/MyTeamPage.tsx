import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useTeamStore, selectTeam } from '@/features/team/store'
import { useRosterStore, selectInventory, selectLineup } from '@/features/team/rosterStore'
import { bestCardFor } from '@/features/team/lib/cardHelpers'
import { Button, Spinner } from '@/shared/ui'
import type { PlayerCard } from '@/shared/api/types'

const RARITY_BORDER: Record<string, string> = {
  COMMON: 'border-slate-400',
  BRONZE: 'border-[#cd7f32]',
  SILVER: 'border-[#c0c0c0]',
  GOLD: 'border-koshien-gold',
  DIAMOND: 'border-[#4fd9ff]',
}

interface FieldSlot {
  id: string
  nameKey: string
}

const FIELD_SECTORS: Array<{ nameKey: string; slots: FieldSlot[] }> = [
  {
    nameKey: 'team.sector.outfield',
    slots: [
      { id: 'LF', nameKey: 'team.slot.lf' },
      { id: 'CF', nameKey: 'team.slot.cf' },
      { id: 'RF', nameKey: 'team.slot.rf' },
    ],
  },
  {
    nameKey: 'team.sector.infield',
    slots: [
      { id: '3B', nameKey: 'team.slot.3b' },
      { id: 'SS', nameKey: 'team.slot.ss' },
      { id: '2B', nameKey: 'team.slot.2b' },
      { id: '1B', nameKey: 'team.slot.1b' },
    ],
  },
  {
    nameKey: 'team.sector.battery',
    slots: [
      { id: 'P', nameKey: 'team.slot.p' },
      { id: 'C', nameKey: 'team.slot.c' },
      { id: 'DH', nameKey: 'team.slot.dh' },
    ],
  },
]

type SavingStatus = 'saving' | 'saved' | 'error' | null

export function MyTeamPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const team = useTeamStore(selectTeam)
  const inventory = useRosterStore(selectInventory)
  const remoteLineup = useRosterStore(selectLineup)
  const { load, updateLineup, hasLoaded, loading } = useRosterStore()

  const [lineup, setLineup] = useState<Record<string, string>>({})
  const [prevRemote, setPrevRemote] = useState<typeof remoteLineup>(null)
  const [activeSlot, setActiveSlot] = useState<string>('P')
  const [savingStatus, setSavingStatus] = useState<SavingStatus>(null)

  if (
    remoteLineup !== prevRemote &&
    remoteLineup?.slots &&
    Object.keys(remoteLineup.slots).length > 0
  ) {
    setPrevRemote(remoteLineup)
    setLineup((current) => (Object.keys(current).length === 0 ? remoteLineup.slots : current))
  }

  const inv = useMemo(() => inventory ?? [], [inventory])

  const assignedCardIds = useMemo(
    () => new Set(Object.values(lineup).filter(Boolean) as string[]),
    [lineup],
  )

  const availableForSelectedSlot = useMemo(() => {
    if (!activeSlot) return []
    const currentId = lineup[activeSlot]
    return inv
      .filter((item) => {
        const card = item.card
        const isTWP = card.position === 'TWP' || card.is_two_way
        if (!isTWP && assignedCardIds.has(card.id) && card.id !== currentId) return false
        if (activeSlot === 'P') return isPitcherCard(card) || isTWP
        if (activeSlot === 'DH') return !isPitcherCard(card) || isTWP
        return card.position === activeSlot
      })
      .sort((a, b) => b.card.overall - a.card.overall)
  }, [inv, activeSlot, assignedCardIds, lineup])

  const cardById = useMemo(
    () => new Map(inv.map((i) => [i.card.id, i.card] as const)),
    [inv],
  )

  useEffect(() => {
    void load()
  }, [load])

  if (!hasLoaded || loading) {
    return <Spinner label={t('common.loading')} className="min-h-screen py-20" />
  }

  const syncLineup = async (next: Record<string, string>) => {
    setLineup(next)
    setSavingStatus('saving')
    try {
      await updateLineup(next)
      setSavingStatus('saved')
      setTimeout(() => setSavingStatus(null), 2000)
    } catch {
      setSavingStatus('error')
    }
  }

  const autoAssignLineup = async () => {
    const assigned: Record<string, string> = {}
    const usedCardIds = new Set<string>()

    const allSlots = FIELD_SECTORS.flatMap((s) => s.slots)

    for (const slot of allSlots) {
      if (slot.id === 'DH' || slot.id === 'P') continue
      const match = bestCardFor(inv, (c) => !usedCardIds.has(c.id) && c.position === slot.id)
      if (match) {
        assigned[slot.id] = match.id
        usedCardIds.add(match.id)
      }
    }

    const pitcher = bestCardFor(
      inv,
      (c) => isPitcherCard(c) || c.position === 'TWP' || c.is_two_way,
    )
    if (pitcher) {
      assigned['P'] = pitcher.id
      if (!(pitcher.position === 'TWP' || pitcher.is_two_way)) usedCardIds.add(pitcher.id)
    }

    const dh = bestCardFor(inv, (c) => {
      const isTWP = c.position === 'TWP' || c.is_two_way
      return (!usedCardIds.has(c.id) || isTWP) && !isPitcherCard(c)
    })
    if (dh) assigned['DH'] = dh.id

    await syncLineup(assigned)
  }

  const handleSelectCardForSlot = async (card: PlayerCard) => {
    const next = { ...lineup }
    for (const [s, c] of Object.entries(next)) {
      if (c === card.id && s !== activeSlot && !(card.position === 'TWP' || card.is_two_way)) {
        delete next[s]
      }
    }
    next[activeSlot] = card.id
    await syncLineup(next)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="team-screen mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-between px-2 py-3 sm:px-4 sm:py-4"
    >
      {/* CABECERA DEL CLUB */}
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b-2 border-koshien-gold pb-3">
        <div className="flex min-w-0 items-center gap-3 sm:gap-4">
          {team ? (
            <div
              className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full border-2 border-white/20 font-sports text-xl text-white shadow-lg sm:h-16 sm:w-16 sm:text-2xl"
              style={{ backgroundColor: team.primary_color }}
            >
              {team.short_name}
            </div>
          ) : null}
          <div className="min-w-0">
            <div className="mb-0.5 flex flex-wrap items-center gap-2">
              <span className="font-vintage text-[10px] uppercase tracking-widest text-koshien-gold sm:text-xs">
                {team ? `${team.city} • ${team.stadium_name}` : t('team.subtitle')}
              </span>
              {savingStatus ? (
                <span
                  className={`rounded border px-1.5 py-0.5 font-vintage text-[9px] uppercase tracking-widest ${
                    savingStatus === 'error'
                      ? 'animate-pulse border-red-400 text-red-400'
                      : 'animate-pulse border-koshien-gold bg-koshien-green text-koshien-gold'
                  }`}
                >
                  {savingStatus === 'saving'
                    ? t('team.saving')
                    : savingStatus === 'saved'
                      ? t('team.saved')
                      : t('team.save_error')}
                </span>
              ) : null}
            </div>
            <h1 className="truncate font-sports text-3xl uppercase leading-none tracking-wide text-koshien-chalk sm:text-4xl">
              {team ? team.name : t('team.title')}
            </h1>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            onClick={() => void autoAssignLineup()}
            className="border border-koshien-gold bg-koshien-green text-koshien-gold hover:bg-koshien-light-green"
          >
            {t('team.auto_lineup')}
          </Button>
          <Button
            variant="ghost"
            onClick={() => navigate('/lobby')}
            className="border border-koshien-border text-koshien-chalk hover:border-koshien-gold"
          >
            {t('team.back_lobby')}
          </Button>
        </div>
      </header>

      {/* CAMPO + CANDIDATOS */}
      <main className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:items-stretch">
        {/* VISTA DEL CAMPO */}
        <section className="relative flex flex-col justify-around overflow-hidden rounded-xl border-2 border-koshien-border bg-koshien-dark p-4 shadow-2xl lg:col-span-9">
          <div className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center opacity-20 select-none">
            <DiamondField />
          </div>

          <span className="relative z-10 mb-3 block font-vintage text-[10px] font-bold uppercase tracking-widest text-koshien-gold sm:text-xs">
            {t('team.click_position')}
          </span>

          <div className="relative z-10 space-y-3">
            {FIELD_SECTORS.map((sector) => (
              <div key={sector.nameKey}>
                <span className="mb-1 block border-b border-koshien-border/60 pb-0.5 font-vintage text-[9px] uppercase tracking-widest text-koshien-gold/80">
                  {t(sector.nameKey)}
                </span>
                <div className="flex flex-wrap justify-center gap-3">
                  {sector.slots.map((slot) => {
                    const assignedId = lineup[slot.id]
                    const assigned = assignedId ? cardById.get(assignedId) : undefined
                    const isSelected = activeSlot === slot.id
                    const isTWP = Boolean(assigned && (assigned.position === 'TWP' || assigned.is_two_way))

                    return (
                      <button
                        key={slot.id}
                        type="button"
                        onClick={() => setActiveSlot(slot.id)}
                        className={`flex min-h-[88px] min-w-[160px] max-w-[220px] flex-1 flex-col justify-between rounded border-2 p-2.5 text-left backdrop-blur-md transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
                          isSelected
                            ? 'scale-105 border-koshien-gold bg-koshien-green/90 shadow-[0_0_15px_rgba(197,160,89,0.4)]'
                            : assigned
                              ? 'border-koshien-border bg-koshien-dark/85 hover:border-koshien-cream/50'
                              : 'border-dashed border-red-500/50 bg-red-950/20 hover:border-red-400/70'
                        }`}
                      >
                        <div className="flex w-full items-center justify-between border-b border-white/10 pb-0.5 text-[10px] font-bold text-koshien-gold">
                          <span className="flex items-center gap-1">
                            {slot.id}
                            {isTWP ? (
                              <span className="rounded bg-koshien-gold px-1 font-extrabold text-koshien-dark">TWP</span>
                            ) : null}
                          </span>
                          <span className="truncate font-vintage text-[9px] font-normal text-koshien-cream/60">
                            {t(slot.nameKey)}
                          </span>
                        </div>

                        {assigned ? (
                          <div className="mt-1 w-full text-left">
                            <div className="truncate font-sports text-lg uppercase leading-tight text-koshien-chalk">
                              {assigned.name}
                            </div>
                            <span className="font-vintage text-[10px] text-koshien-cream/70">
                              {assigned.overall} OVR | C:{assigned.contact} P:{assigned.power}
                            </span>
                          </div>
                        ) : (
                          <span className="my-auto block py-1 text-center font-sports text-xs font-bold uppercase text-red-400">
                            [ {t('team.empty_slot')} ]
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* PANEL DE CANDIDATOS */}
        <aside className="flex flex-col rounded-xl border-2 border-koshien-border bg-koshien-dark p-3 shadow-2xl lg:col-span-3">
          <div className="mb-3 border-b border-koshien-border pb-2">
            <span className="block font-vintage text-[10px] uppercase tracking-widest text-koshien-cream/60">
              {t('team.candidates_for')}
            </span>
            <h3 className="font-sports text-xl uppercase text-koshien-gold">
              {t('team.position')}: {activeSlot}
            </h3>
          </div>

          <div className="max-h-[50vh] space-y-2 overflow-y-auto pr-1">
            {availableForSelectedSlot.length === 0 ? (
              <p className="py-8 text-center font-vintage text-xs text-koshien-cream/50">
                {t('team.no_candidates', { pos: activeSlot })}
              </p>
            ) : (
              availableForSelectedSlot.map((item) => (
                <CandidateRow
                  key={item.inventory_id}
                  card={item.card}
                  selected={lineup[activeSlot] === item.card.id}
                  onSelect={() => void handleSelectCardForSlot(item.card)}
                />
              ))
            )}
          </div>
        </aside>
      </main>

      <footer className="mt-4 text-center font-vintage text-[9px] uppercase tracking-widest text-koshien-border sm:text-[10px]">
        KOSHIEN LINEUP & FIELD ENGINE • 2026
      </footer>
    </motion.div>
  )
}

function DiamondField() {
  return (
    <svg viewBox="0 0 400 400" className="h-[480px] w-[480px]">
      <path d="M 200 350 L 50 150 A 210 210 0 0 1 350 150 Z" fill="none" stroke="#C5A059" strokeWidth="2" strokeDasharray="4 4" />
      <line x1="200" y1="350" x2="30" y2="130" stroke="#C5A059" strokeWidth="2" />
      <line x1="200" y1="350" x2="370" y2="130" stroke="#C5A059" strokeWidth="2" />
      <polygon points="200,350 280,270 200,190 120,270" fill="none" stroke="#C5A059" strokeWidth="2" />
      <circle cx="200" cy="270" r="18" fill="none" stroke="#C5A059" strokeWidth="1.5" />
      <polygon points="200,352 193,345 193,340 207,340 207,345" fill="#C5A059" />
    </svg>
  )
}

function isPitcherCard(card: PlayerCard): boolean {
  return card.position === 'SP' || card.position === 'RP' || card.position === 'CP'
}

function CandidateRow({
  card,
  selected,
  onSelect,
}: {
  card: PlayerCard
  selected: boolean
  onSelect: () => void
}) {
  const { t } = useTranslation()
  const rarity = card.rarity?.toUpperCase() ?? 'COMMON'
  const border = RARITY_BORDER[rarity] ?? 'border-slate-400'

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`flex w-full items-center gap-2 rounded border border-l-4 px-2 py-1.5 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
        selected
          ? 'border-koshien-gold bg-koshien-green'
          : `${border} bg-koshien-dark/60 hover:bg-koshien-green/40`
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="truncate font-sports text-base font-bold uppercase leading-tight text-koshien-chalk">
          {card.name}
        </div>
        <div className="font-vintage text-[9px] uppercase tracking-widest text-koshien-cream/70">
          {card.position} • #{card.number} • {t('card.power')} {card.power} • {t('card.contact')}{' '}
          {card.contact}
        </div>
      </div>
      <div className="flex flex-shrink-0 flex-col items-center rounded border border-koshien-border bg-koshien-green/50 px-1.5 py-0.5">
        <span className="font-sports text-base font-bold leading-none text-koshien-gold">
          {card.overall}
        </span>
        <span className="font-vintage text-[7px] uppercase text-koshien-cream/60">OVR</span>
      </div>
      {selected ? <span className="flex-shrink-0 font-sports text-base text-koshien-gold">✓</span> : null}
    </button>
  )
}
