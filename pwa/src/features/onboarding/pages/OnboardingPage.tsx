import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { ApiError } from '@/shared/api/errors'
import { Button } from '@/shared/ui/Button'
import { InputField } from '@/shared/ui/InputField'
import { createTeam, getCpuTeams, updateBaseFranchise } from '@/features/team/api'
import { claimStarterPack } from '@/features/shop/api'
import { useTeamStore } from '@/features/team/store'
import { useAuthStore } from '@/features/auth/store'
import type { Franchise, PlayerCard as PlayerCardData, UserTeam } from '@/shared/api/types'
import { FranchiseCarousel } from '../components/FranchiseCarousel'
import { PlayerCardReveal } from '../components/PlayerCardReveal'

type Step = 'CREATE_TEAM' | 'SELECT_FRANCHISE' | 'PACK_UNBOX' | 'SHOW_CARDS'

const PRESET_COLORS = [
  { primary: '#C5A059', secondary: '#1A3323', name: 'Dorado / Verde' },
  { primary: '#005A9C', secondary: '#FFFFFF', name: 'Azul Real / Blanco' },
  { primary: '#132448', secondary: '#BD3039', name: 'Marina / Rojo' },
  { primary: '#E3D4AD', secondary: '#0C2340', name: 'Crema / Azul Noche' },
]

const RARITY_WEIGHTS: Record<string, number> = {
  DIAMOND: 4,
  GOLD: 3,
  SILVER: 2,
  BRONZE: 1,
  COMMON: 0,
}

const FALLBACK_FRANCHISE = 'LAA'

const DEFAULT_PRIMARY = '#C5A059'
const DEFAULT_SECONDARY = '#1A3323'

interface TeamForm {
  name: string
  short_name: string
  city: string
  stadium_name: string
  primary_color: string
  secondary_color: string
}

export function OnboardingPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setTeam = useTeamStore((state) => state.setTeam)
  const setOnboardingComplete = useAuthStore((state) => state.setOnboardingComplete)

  const [step, setStep] = useState<Step>(
    useTeamStore.getState().team ? 'SELECT_FRANCHISE' : 'CREATE_TEAM',
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [teamForm, setTeamForm] = useState<TeamForm>({
    name: '',
    short_name: '',
    city: 'Zapopan',
    stadium_name: 'Estadio Municipal',
    primary_color: DEFAULT_PRIMARY,
    secondary_color: DEFAULT_SECONDARY,
  })

  const [franchises, setFranchises] = useState<Franchise[]>([])
  const [selectedFranchise, setSelectedFranchise] = useState<string>('')
  const [claimedCards, setClaimedCards] = useState<PlayerCardData[]>([])
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set())
  const [revealAll, setRevealAll] = useState(false)

  useEffect(() => {
    if (step !== 'SELECT_FRANCHISE' || franchises.length > 0) return
    let active = true
    const load = async () => {
      try {
        const teams = await getCpuTeams()
        if (!active) return
        setFranchises(teams)
        if (teams.length > 0) {
          const first = teams[0]
          if (first) setSelectedFranchise((current) => current || first.id)
        }
      } catch {
        if (active) setError(t('onboarding.franchise.error_load'))
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [step, franchises.length, t])

  const setField = <K extends keyof TeamForm>(key: K, value: string) => {
    setTeamForm((current) => ({ ...current, [key]: value }))
  }

  const handleCreateTeam = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!teamForm.name.trim() || !teamForm.short_name.trim()) {
      setError(t('onboarding.create.error_required'))
      return
    }

    setLoading(true)
    setError(null)
    try {
      const created: UserTeam = await createTeam({
        ...teamForm,
        short_name: teamForm.short_name.trim().toUpperCase(),
        base_franchise: FALLBACK_FRANCHISE,
      })
      setTeam(created)
      setStep('SELECT_FRANCHISE')
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message || t('onboarding.create.error_generic')
          : t('onboarding.create.error_generic')
      setError(message.includes('ya tiene un club') ? t('onboarding.create.error_exists') : message)
    } finally {
      setLoading(false)
    }
  }

  const handleClaimStarterPack = async () => {
    if (!selectedFranchise) {
      setError(t('onboarding.franchise.error_required'))
      return
    }

    setLoading(true)
    setError(null)
    try {
      const team = await updateBaseFranchise(selectedFranchise)
      setTeam(team)
      const response = await claimStarterPack(selectedFranchise)
      setClaimedCards(response.cards ?? [])
      setStep('PACK_UNBOX')
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message || t('onboarding.franchise.error_generic') : t('onboarding.franchise.error_generic')
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const sortedCards = useMemo(() => {
    return [...claimedCards].sort((a, b) => {
      const rarityA = RARITY_WEIGHTS[a.rarity?.toUpperCase()] ?? 0
      const rarityB = RARITY_WEIGHTS[b.rarity?.toUpperCase()] ?? 0
      if (rarityB !== rarityA) return rarityB - rarityA
      return b.overall - a.overall
    })
  }, [claimedCards])

  if (step === 'CREATE_TEAM') {
    return (
      <main className="min-h-dvh bg-koshien-dark px-4 pb-[max(2rem,calc(env(safe-area-inset-bottom)+1rem))] pt-[max(1.5rem,env(safe-area-inset-top))]">
        <div className="mx-auto w-full max-w-xl">
          <header className="mb-6 text-center">
            <span className="font-vintage text-[10px] uppercase tracking-[0.28em] text-koshien-gold">
              {t('onboarding.create.step_label')}
            </span>
            <h1 className="mt-2 font-sports text-3xl font-bold uppercase leading-none tracking-wide text-koshien-chalk">
              {t('onboarding.create.title')}
            </h1>
            <p className="mt-2 font-vintage text-xs uppercase tracking-[0.18em] text-koshien-cream/70">
              {t('onboarding.create.subtitle')}
            </p>
          </header>

          {error ? (
            <div
              role="alert"
              className="mb-4 rounded-xl border border-red-500/50 bg-red-900/40 px-4 py-3 font-vintage text-xs text-red-300"
            >
              {error}
            </div>
          ) : null}

          <form
            onSubmit={handleCreateTeam}
            noValidate
            className="space-y-4 rounded-2xl border border-koshien-border bg-koshien-dark/80 p-5"
          >
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <InputField
                  label={t('onboarding.create.name')}
                  name="name"
                  placeholder="Tigres"
                  maxLength={40}
                  autoComplete="off"
                  value={teamForm.name}
                  onChange={(event) => setField('name', event.target.value)}
                />
              </div>
              <div>
                <InputField
                  label={t('onboarding.create.short_name')}
                  name="short_name"
                  placeholder="TIG"
                  maxLength={3}
                  autoComplete="off"
                  className="uppercase"
                  value={teamForm.short_name}
                  onChange={(event) =>
                    setField('short_name', event.target.value.toUpperCase())
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <InputField
                label={t('onboarding.create.city')}
                name="city"
                value={teamForm.city}
                onChange={(event) => setField('city', event.target.value)}
              />
              <InputField
                label={t('onboarding.create.stadium')}
                name="stadium_name"
                value={teamForm.stadium_name}
                onChange={(event) => setField('stadium_name', event.target.value)}
              />
            </div>

            <fieldset>
              <legend className="mb-1.5 font-vintage text-xs uppercase tracking-widest text-koshien-cream">
                {t('onboarding.create.colors')}
              </legend>
              <div className="grid grid-cols-2 gap-2">
                {PRESET_COLORS.map((color) => {
                  const selected = teamForm.primary_color === color.primary
                  return (
                    <button
                      key={color.primary}
                      type="button"
                      aria-pressed={selected}
                      onClick={() =>
                        setTeamForm((current) => ({
                          ...current,
                          primary_color: color.primary,
                          secondary_color: color.secondary,
                        }))
                      }
                      className={`flex items-center justify-between rounded-xl border-2 px-3 py-2 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
                        selected
                          ? 'border-koshien-gold bg-koshien-green'
                          : 'border-koshien-border bg-koshien-dark hover:border-koshien-gold/50'
                      }`}
                    >
                      <span className="font-vintage text-[11px] uppercase text-koshien-cream">
                        {color.name}
                      </span>
                      <span className="flex gap-1">
                        <span
                          aria-hidden
                          className="h-4 w-4 rounded-full border border-white/20"
                          style={{ backgroundColor: color.primary }}
                        />
                        <span
                          aria-hidden
                          className="h-4 w-4 rounded-full border border-white/20"
                          style={{ backgroundColor: color.secondary }}
                        />
                      </span>
                    </button>
                  )
                })}
              </div>
            </fieldset>

            <Button type="submit" size="lg" disabled={loading} className="mt-2 w-full">
              {loading ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : null}
              {loading
                ? t('onboarding.create.submitting')
                : t('onboarding.create.submit')}
            </Button>
          </form>
        </div>
      </main>
    )
  }

  if (step === 'SELECT_FRANCHISE') {
    return (
      <main className="min-h-dvh bg-koshien-dark px-4 pb-[max(2rem,calc(env(safe-area-inset-bottom)+1rem))] pt-[max(1.5rem,env(safe-area-inset-top))]">
        <div className="mx-auto w-full max-w-4xl">
          <header className="mb-6 text-center">
            <span className="font-vintage text-[10px] uppercase tracking-[0.28em] text-koshien-gold">
              {t('onboarding.franchise.step_label')}
            </span>
            <h1 className="mt-2 font-sports text-3xl font-bold uppercase leading-none tracking-wide text-koshien-chalk">
              {t('onboarding.franchise.title')}
            </h1>
            <p className="mx-auto mt-2 max-w-md font-vintage text-xs uppercase tracking-[0.18em] text-koshien-cream/70">
              {t('onboarding.franchise.subtitle', { team: teamForm.name })}
            </p>
          </header>

          {error ? (
            <div
              role="alert"
              className="mb-4 rounded-xl border border-red-500/50 bg-red-900/40 px-4 py-3 font-vintage text-xs text-red-300"
            >
              {error}
            </div>
          ) : null}

          {franchises.length > 0 ? (
            <FranchiseCarousel
              teams={franchises}
              selectedTeamId={selectedFranchise}
              onSelectTeam={(teamId) => {
                setSelectedFranchise(teamId)
                setError(null)
              }}
            />
          ) : (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-koshien-gold" aria-hidden />
            </div>
          )}

          <Button
            type="button"
            size="lg"
            disabled={loading || franchises.length === 0}
            onClick={() => void handleClaimStarterPack()}
            className="mt-6 w-full"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : null}
            {loading
              ? t('onboarding.franchise.claiming')
              : t('onboarding.franchise.claim')}
          </Button>
        </div>
      </main>
    )
  }

  const cardsRevealed = sortedCards.length > 0 && sortedCards.every((card) => revealedIds.has(card.id))

  return (
    <main className="pack-screen min-h-dvh px-4 pb-[max(2rem,calc(env(safe-area-inset-bottom)+1rem))] pt-[max(1.5rem,env(safe-area-inset-top))]">
      <div aria-hidden className="pack-screen__bg" />
      <div className="pack-screen__content">
      <AnimatePresence mode="wait">
        {step === 'PACK_UNBOX' ? (
          <motion.div
            key="pack"
            exit={{ opacity: 0, scale: 1.15, rotate: 6, transition: { duration: 0.45, ease: 'easeIn' } }}
          >
            <div className="mx-auto flex w-full max-w-md flex-col items-center justify-center gap-6 pt-10 text-center">
              <span className="animate-pulse font-vintage text-xs uppercase tracking-[0.28em] text-koshien-gold">
                {t('onboarding.pack.welcome')}
              </span>
              <h1 className="font-sports text-3xl font-bold uppercase leading-none tracking-wide text-koshien-chalk">
                {t('onboarding.pack.title', { team: teamForm.name })}
              </h1>

              <motion.button
                type="button"
                aria-label={t('onboarding.pack.click_to_open')}
                onClick={() => setStep('SHOW_CARDS')}
                className="group relative mt-4 cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-8 focus-visible:outline-koshien-gold"
                animate={{ y: [0, -14, 0], scale: [1, 1.035, 1] }}
                transition={{ y: { duration: 2.6, repeat: Infinity, ease: 'easeInOut' }, scale: { duration: 2.6, repeat: Infinity, ease: 'easeInOut' } }}
                whileHover={{ scale: 1.08 }}
                whileTap={{ scale: 0.95 }}
              >
                {/* Brillo de barrido */}
                <span
                  aria-hidden
                  className="pointer-events-none absolute inset-y-0 z-10 w-1/3 -skew-x-12 bg-gradient-to-r from-transparent via-white/50 to-transparent"
                  style={{ left: '-40%', animation: 'pack-shine 2.4s linear infinite' }}
                />
                <motion.div
                  className="flex h-80 w-60 flex-col items-center justify-between rounded-2xl border-4 border-koshien-chalk bg-gradient-to-br from-[#d4af37] via-[#c5a059] to-[#8a6d3b] p-6"
                  animate={{
                    boxShadow: [
                      '0 0 60px rgba(197,160,89,0.5)',
                      '0 0 100px rgba(212,175,55,0.9)',
                      '0 0 60px rgba(197,160,89,0.5)',
                    ],
                  }}
                  transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
                >
                  <span className="relative z-10 rounded-full bg-gradient-to-r from-white to-yellow-200 px-4 py-1 font-vintage text-[10px] font-bold uppercase tracking-widest text-[#1a1a00]">
                    {t('onboarding.pack.badge')}
                  </span>
                  <motion.span
                    className="relative z-10 text-8xl"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                  >
                    ⚾
                  </motion.span>
                  <div className="relative z-10 text-center">
                    <span className="block font-sports text-4xl font-bold uppercase tracking-wider text-white drop-shadow-lg">
                      {t('onboarding.pack.cards_count', { count: claimedCards.length })}
                    </span>
                    <span className="mt-2 block font-vintage text-[11px] uppercase tracking-widest text-koshien-chalk">
                      {t('onboarding.pack.click_to_open')}
                    </span>
                  </div>
                </motion.div>
              </motion.button>

              <p className="animate-pulse font-vintage text-xs uppercase tracking-[0.18em] text-koshien-gold">
                {t('onboarding.pack.hint')}
              </p>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="cards"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1, transition: { duration: 0.3, ease: 'easeOut' } }}
          >
            <div className="mx-auto w-full">
              <header className="pack-header">
                <h1 className="pack-title font-sports font-bold uppercase text-koshien-gold">
                  {t('onboarding.cards.title')}
                </h1>
                <p className="pack-subtitle font-vintage uppercase text-koshien-cream">
                  {t('onboarding.cards.subtitle')}
                </p>
              </header>

              <div className="mb-8 flex justify-center">
                <button
                  type="button"
                  disabled={cardsRevealed}
                  onClick={() => {
                    setRevealAll(true)
                    setRevealedIds(new Set(sortedCards.map((card) => card.id)))
                  }}
                  className="reveal-all-button font-vintage uppercase tracking-[0.06em]"
                >
                  {cardsRevealed
                    ? t('onboarding.cards.revealed_all')
                    : t('onboarding.cards.reveal_all')}
                </button>
              </div>

              <div className="pack-grid">
                {sortedCards.map((card, index) => (
                  <motion.div
                    key={card.id}
                    initial={{ opacity: 0, y: 28, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.4, ease: 'easeOut', delay: index * 0.06 }}
                  >
                    <PlayerCardReveal
                      card={card}
                      revealed={revealedIds.has(card.id)}
                      revealAll={revealAll}
                      index={index}
                      onReveal={() => {
                        setRevealedIds((current) => {
                          const next = new Set(current)
                          next.add(card.id)
                          return next
                        })
                      }}
                    />
                  </motion.div>
                ))}
              </div>

              <div className="mt-10 flex justify-center">
                <Button
                  type="button"
                  size="lg"
                  onClick={() => {
                    setOnboardingComplete(true)
                    navigate('/lobby', { replace: true })
                  }}
                  className="w-full max-w-sm"
                >
                  {t('onboarding.cards.to_lobby')}
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      </div>
    </main>
  )
}
