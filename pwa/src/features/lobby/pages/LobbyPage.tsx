import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { Languages, LogOut } from 'lucide-react'
import { useAuthStore, selectUser } from '@/features/auth/store'
import { useTeamStore, selectTeam } from '@/features/team/store'
import { getCpuTeams, getTeamStats } from '@/features/team/api'
import { useLobbyStore } from '@/features/lobby/store'
import { resetSessionStores } from '@/shared/lib/sessionCleanup'
import { FranchiseCarousel } from '@/features/onboarding/components/FranchiseCarousel'
import { Button, Spinner } from '@/shared/ui'
import type { Difficulty, Franchise, GameMode, PlayerPosition, TeamStatsResponse } from '@/shared/api/types'

const DIFFICULTIES: Difficulty[] = ['EASY', 'MEDIUM', 'HARD']
const INNINGS = [3, 6, 9]
const POSITIONS: PlayerPosition[] = ['HOME', 'AWAY']

const MODE_STYLES = {
  active: 'border-koshien-gold bg-koshien-green sm:border-2 shadow-[0_0_15px_rgba(197,160,89,0.3)]',
  inactive: 'border-koshien-border bg-koshien-dark/60 opacity-60 hover:opacity-100',
}

export function LobbyPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const user = useAuthStore(selectUser)
  const signOut = useAuthStore((state) => state.signOut)
  const team = useTeamStore(selectTeam)
  const config = useLobbyStore((s) => s.config)
  const setConfig = useLobbyStore((s) => s.setConfig)

  const [teams, setTeams] = useState<Franchise[]>([])
  const [stats, setStats] = useState<TeamStatsResponse | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    getCpuTeams()
      .then(setTeams)
      .catch(() => setLoadError(t('lobby.error_load')))
  }, [t])

  useEffect(() => {
    getTeamStats()
      .then(setStats)
      .catch(() => undefined)
  }, [])

  const toggleLanguage = () => {
    const next = (i18n.language ?? 'es').startsWith('es') ? 'en' : 'es'
    void i18n.changeLanguage(next)
  }

  const handleLogout = () => {
    resetSessionStores()
    signOut()
  }

  const handleCreate = useCallback(() => {
    navigate('/roster/pending')
  }, [navigate])

  const handleSelectMode = (mode: GameMode) => {
    setConfig({ gameMode: mode })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-between px-2 py-3 sm:px-4 sm:py-4"
    >
      <header className="mx-auto mb-4 flex w-full max-w-7xl flex-wrap items-center justify-between gap-2 rounded border border-koshien-gold bg-koshien-dark p-2 shadow-scoreboard sm:rounded-lg sm:border-2 sm:p-3">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <div className="flex-shrink-0 rounded border border-koshien-gold bg-koshien-green px-2 py-1 text-center sm:px-3">
            <span className="font-sports text-sm text-koshien-gold sm:text-xl">LVL 12</span>
          </div>
          <div className="min-w-0">
            <span className="block font-vintage text-[9px] uppercase tracking-widest text-koshien-gold sm:text-[10px]">
              {t('lobby.manager')}
            </span>
            <h2 className="truncate font-sports text-lg uppercase leading-none text-koshien-chalk sm:text-2xl">
              {(user?.username ?? '').substring(0, 12)}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-1 sm:gap-2">
          <button
            type="button"
            onClick={toggleLanguage}
            className="inline-flex items-center gap-1 rounded border border-koshien-gold bg-koshien-green px-2 py-1 font-vintage text-[9px] uppercase tracking-widest text-koshien-chalk transition-colors hover:bg-koshien-light-green focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:px-3 sm:text-[10px]"
          >
            <Languages className="h-3.5 w-3.5" aria-hidden />
            {(i18n.language ?? 'es').startsWith('es') ? 'EN' : 'ES'}
          </button>

          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center gap-1 rounded border border-koshien-border px-2 py-1 font-vintage text-[9px] uppercase tracking-widest text-koshien-cream transition-colors hover:border-koshien-gold hover:bg-koshien-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:px-3 sm:text-[10px]"
          >
            <LogOut className="h-3.5 w-3.5" aria-hidden />
            {t('lobby.logout')}
          </button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-3 py-2 sm:gap-4 sm:py-3 lg:flex-row lg:items-stretch">
        {/* PANEL IZQUIERDO: MI CLUB / PREPARACIÓN */}
        <section className="flex w-full flex-col justify-between rounded border border-koshien-border bg-koshien-dark p-3 shadow-scoreboard sm:p-4 lg:w-5/12 lg:border-2">
          <div>
            <span className="mb-1 block font-vintage text-[9px] uppercase tracking-widest text-koshien-gold sm:text-xs">
              {t('lobby.my_club')}
            </span>
            <h3 className="mb-2 border-b border-koshien-border pb-1 font-sports text-2xl uppercase text-koshien-chalk sm:mb-4 sm:text-3xl">
              {t('lobby.preparation')}
            </h3>

            {team ? (
              <div className="mb-3 rounded border border-koshien-gold/40 bg-koshien-dark p-2 sm:mb-4 sm:p-3">
                <div className="mb-2 flex items-center justify-between gap-2 sm:mb-3">
                  <div className="flex min-w-0 items-center gap-2 sm:gap-3">
                    <div
                      className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full border-2 border-white/20 font-sports text-sm text-white shadow sm:h-14 sm:w-14 sm:text-xl"
                      style={{ backgroundColor: team.primary_color }}
                    >
                      {team.short_name?.substring(0, 2)}
                    </div>
                    <div className="min-w-0 overflow-hidden">
                      <span className="block truncate font-vintage text-[8px] uppercase tracking-widest text-koshien-cream/60 sm:text-[10px]">
                        {team.city}
                      </span>
                      <h4 className="truncate font-sports text-lg uppercase text-koshien-chalk sm:text-2xl">
                        {team.name}
                      </h4>
                    </div>
                  </div>
                  <div className="flex-shrink-0 rounded border border-white bg-koshien-gold px-1.5 py-0.5 font-sports text-sm font-extrabold text-koshien-dark shadow sm:px-2 sm:text-lg">
                    {stats?.overall ?? '--'}
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <div className="space-y-2 pt-1 sm:space-y-3 sm:pt-2">
            <button
              type="button"
              onClick={() => navigate('/team')}
              className="flex w-full items-center justify-between rounded border border-koshien-gold bg-koshien-green px-3 py-2 font-sports text-lg uppercase text-koshien-chalk shadow-md transition-all hover:bg-koshien-light-green active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:py-3 sm:text-2xl"
            >
              <span className="truncate">🛡️ {t('menu.team')}</span>
              <span className="font-vintage text-xs text-koshien-gold">→</span>
            </button>

            <button
              type="button"
              onClick={() => navigate('/showcase')}
              className="flex w-full items-center justify-between rounded border border-koshien-border bg-koshien-dark px-3 py-2 font-sports text-lg uppercase text-koshien-chalk shadow-md transition-all hover:border-koshien-gold hover:bg-koshien-green active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:py-3 sm:text-2xl"
            >
              <span className="truncate">🎴 {t('menu.album')}</span>
              <span className="font-vintage text-xs text-koshien-cream">→</span>
            </button>
          </div>
        </section>

        {/* PANEL DERECHO: MATCHMAKING */}
        <section className="flex w-full flex-col justify-between rounded border border-koshien-gold bg-koshien-dark p-3 shadow-scoreboard sm:p-4 lg:w-7/12 lg:border-2">
          <div>
            <span className="mb-1 block font-vintage text-[9px] uppercase tracking-widest text-koshien-gold sm:text-xs">
              {t('lobby.matchmaking')}
            </span>
            <h3 className="mb-2 border-b border-koshien-border pb-1 font-sports text-2xl uppercase text-koshien-chalk sm:mb-4 sm:text-3xl">
              {t('lobby.game_mode')}
            </h3>

            {/* SELECTOR DE MODO */}
            <div className="mb-3 grid grid-cols-1 gap-2 sm:mb-4 sm:grid-cols-2 sm:gap-3">
              <button
                type="button"
                onClick={() => handleSelectMode('PVE')}
                className={`flex flex-col items-center justify-center rounded p-2 text-center transition-all sm:p-3 ${MODE_STYLES[config.gameMode === 'PVE' ? 'active' : 'inactive']}`}
              >
                <span className="mb-1 font-sports text-lg leading-none text-koshien-chalk sm:text-2xl">
                  {t('lobby.vs_cpu')}
                </span>
                <span className="font-vintage text-[8px] uppercase text-koshien-cream sm:text-[10px]">
                  {t('lobby.vs_cpu_desc')}
                </span>
              </button>

              <button
                type="button"
                disabled
                className={`flex flex-col items-center justify-center rounded p-2 text-center opacity-40 transition-all sm:p-3 ${MODE_STYLES.inactive}`}
              >
                <span className="mb-1 font-sports text-lg leading-none text-koshien-chalk sm:text-2xl">
                  {t('lobby.pvp')}
                </span>
                <span className="font-vintage text-[8px] uppercase text-koshien-cream sm:text-[10px]">
                  {t('lobby.not_available')}
                </span>
              </button>
            </div>

            {/* CARRUSEL DE RIVAL CPU */}
            <div className="mb-3 sm:mb-4">
              <div className="mb-1 flex items-center justify-between sm:mb-2">
                <span className="font-vintage text-[8px] font-bold uppercase tracking-widest text-koshien-gold sm:text-xs">
                  ★ {t('lobby.select_rival')} ★
                </span>
                {teams.length > 0 ? (
                  <span className="font-vintage text-[8px] text-koshien-cream/60 sm:text-[10px]">
                    {teams.findIndex((t) => t.id === config.rivalId) + 1 || 1}/{teams.length}
                  </span>
                ) : null}
              </div>

              {loadError ? (
                <p className="font-vintage text-xs uppercase text-red-400">{loadError}</p>
              ) : teams.length === 0 ? (
                <Spinner label={t('common.loading')} className="py-12" />
              ) : (
                <FranchiseCarousel
                  teams={teams}
                  selectedTeamId={config.rivalId}
                  onSelectTeam={(rivalId) => setConfig({ rivalId })}
                />
              )}
            </div>

            {/* CONFIGURACIÓN: DIFICULTAD / INNINGS / POSICIÓN */}
            <div className="grid grid-cols-1 gap-2 sm:mb-1 sm:grid-cols-3 sm:gap-3">
              <ConfigBox title={t('lobby.cpu_difficulty')}>
                <div className="grid grid-cols-3 gap-1">
                  {DIFFICULTIES.map((d) => (
                    <OptionButton
                      key={d}
                      active={config.difficulty === d}
                      onClick={() => setConfig({ difficulty: d })}
                    >
                      {t(`lobby.diff_${d.toLowerCase()}`)}
                    </OptionButton>
                  ))}
                </div>
              </ConfigBox>

              <ConfigBox title={t('lobby.innings')}>
                <div className="grid grid-cols-3 gap-1">
                  {INNINGS.map((n) => (
                    <OptionButton
                      key={n}
                      active={config.innings === n}
                      onClick={() => setConfig({ innings: n })}
                    >
                      {n}
                    </OptionButton>
                  ))}
                </div>
              </ConfigBox>

              <ConfigBox title={t('lobby.position')}>
                <div className="grid grid-cols-2 gap-1">
                  {POSITIONS.map((p) => (
                    <OptionButton
                      key={p}
                      active={config.playerPosition === p}
                      onClick={() => setConfig({ playerPosition: p })}
                    >
                      {p === 'HOME' ? t('lobby.position_home') : t('lobby.position_away')}
                    </OptionButton>
                  ))}
                </div>
              </ConfigBox>
            </div>
          </div>

          <Button
            size="lg"
            disabled={!config.rivalId}
            onClick={handleCreate}
            className="mt-2 w-full border border-koshien-gold bg-koshien-green text-koshien-gold hover:bg-koshien-light-green sm:mt-3 sm:border-2 sm:text-2xl"
          >
            {t('lobby.start_pve', { innings: config.innings })}
          </Button>
        </section>
      </main>

      <footer className="mt-1 text-center font-vintage text-[8px] uppercase tracking-widest text-koshien-border sm:mt-2 sm:text-[10px]">
        KOSHIEN • RESPONSIVE
      </footer>
    </motion.div>
  )
}

function ConfigBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded border border-koshien-border bg-koshien-dark p-2 sm:p-2.5">
      <span className="mb-1 block text-center font-vintage text-[8px] font-bold uppercase text-koshien-cream sm:text-[10px]">
        {title}
      </span>
      {children}
    </div>
  )
}

function OptionButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`cursor-pointer rounded py-0.5 font-sports text-[9px] uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:py-1 sm:text-sm ${
        active
          ? 'border border-koshien-gold bg-koshien-light-green text-koshien-chalk'
          : 'bg-koshien-green/50 text-koshien-cream/60 opacity-50 hover:opacity-100'
      }`}
    >
      {children}
    </button>
  )
}
