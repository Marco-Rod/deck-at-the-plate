import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import styles from './StadiumPage.module.css'
import { useGameStore } from '@/features/game/store'
import { useGameSocket } from '@/features/game/hooks/useGameSocket'
import { useEventSequencer } from '@/features/game/hooks/useEventSequencer'
import { normalizeEventName } from '@/features/game/lib/eventNormalizer'
import { isIntroShown, markIntroShown } from '@/features/game/lib/persistence'
import { getTeam } from '@/features/team/api'
import { getCard } from '@/features/cards/api'
import { PitchSelectorPanel } from '@/features/game/components/pitch/PitchSelectorPanel'
import { GameIntroModal } from '@/features/game/components/modals/GameIntroModal'
import { PlayResultOverlay } from '@/features/game/components/modals/PlayResultOverlay'
import { InningTransitionModal } from '@/features/game/components/modals/InningTransitionModal'
import { GameOverModal } from '@/features/game/components/modals/GameOverModal'
import { QuitGameModal } from '@/features/game/components/modals/QuitGameModal'
import { RivalPitcherChangeModal } from '@/features/game/components/modals/RivalPitcherChangeModal'
import { ChangePitcherModal } from '@/features/game/components/modals/ChangePitcherModal'
import { getAvailablePitchers } from '@/features/game/api'
import type {
  GameStateWS,
  PitchAttribute,
  PlayerCard,
  PlayerGameData,
  PlayerRole,
  PlayerStat,
} from '@/shared/api/types'

// ============================================================================
// Helpers
// ============================================================================

function statValue(stats: PlayerStat[] | undefined, labels: string[], fallback = 0): number {
  if (!stats) return fallback
  const found = stats.find((s) => labels.includes(s.label.toUpperCase()) || labels.includes(s.label))
  return found ? found.val : fallback
}

interface PitcherSummary {
  id: string
  name: string
  number: string
  overall: number
  velocity: number
  control: number
  movement: number
  stamina: number
  pitchCount: number
  rarity: string
  repertoire: PitchAttribute[] | null
}

interface BatterSummary {
  id: string
  name: string
  number: string
  overall: number
  contact: number
  power: number
  speed: number
  rarity: string
}

interface BullpenPitcher extends PlayerGameData {
  already_used?: boolean
}

const FALLBACK_PITCHER: PitcherSummary = {
  id: '',
  name: 'LANZADOR',
  number: '0',
  overall: 0,
  velocity: 0,
  control: 0,
  movement: 0,
  stamina: 0,
  pitchCount: 0,
  rarity: 'COMMON',
  repertoire: null,
}

const FALLBACK_BATTER: BatterSummary = {
  id: '',
  name: 'BATEADOR',
  number: '0',
  overall: 0,
  contact: 0,
  power: 0,
  speed: 0,
  rarity: 'COMMON',
}

function toPitcherSummary(p: PlayerGameData | undefined): PitcherSummary {
  if (!p) return FALLBACK_PITCHER
  // El backend reporta fatiga (0 = fresco, 100 = agotado), mientras que la
  // barra representa la stamina restante. Las estadísticas de respaldo ya
  // vienen expresadas como stamina y no necesitan inversión.
  const stamina =
    p.fatigue_level == null
      ? statValue(p.stats, ['STAM', 'STAMINA'], 100)
      : 100 - p.fatigue_level
  return {
    id: p.id,
    name: p.name,
    number: p.number,
    overall: p.overall,
    velocity: statValue(p.stats, ['VEL', 'VELO', 'VELOCITY']),
    control: statValue(p.stats, ['CTRL', 'CONTROL']),
    movement: statValue(p.stats, ['MOV', 'MOVEMENT']),
    stamina: Math.round(Math.min(100, Math.max(0, stamina))),
    pitchCount: p.pitch_count ?? 0,
    rarity: p.rarity ?? 'COMMON',
    repertoire: p.repertoire ?? null,
  }
}

function toBatterSummary(b: PlayerGameData | undefined): BatterSummary {
  if (!b) return FALLBACK_BATTER
  return {
    id: b.id,
    name: b.name,
    number: b.number,
    overall: b.overall,
    contact: statValue(b.stats, ['CON', 'CONTACT']),
    power: statValue(b.stats, ['POW', 'POWER']),
    speed: statValue(b.stats, ['SPD', 'SPEED']),
    rarity: b.rarity ?? 'COMMON',
  }
}

// Mapea una carta (PlayerCard) a PlayerGameData para poblar las tarjetas de
// pitcher/bateador cuando el INIT_GAME_STATE solo trae IDs en state_data.
function toGamePlayer(card: PlayerCard, role: PlayerRole): PlayerGameData {
  const stats: PlayerStat[] = [
    { label: 'VEL', val: card.velocity },
    { label: 'CTRL', val: card.control },
    { label: 'MOV', val: card.movement },
    { label: 'CON', val: card.contact },
    { label: 'POW', val: card.power },
  ]
  const isPitcher = card.position === 'P' || card.position === 'SP'
  if (!isPitcher) stats.push({ label: 'SPD', val: Math.round((card.contact + card.power) / 2) })
  return {
    id: card.id,
    name: card.name,
    number: card.number,
    overall: card.overall,
    position: card.position,
    photo: '',
    role,
    rarity: card.rarity,
    repertoire: card.repertoire ?? undefined,
    stats,
  }
}

function resolveRole(userRole: 'HOME' | 'AWAY', isTop: boolean): PlayerRole {
  // En casa se picha al inicio (parte alta); visita batea.
  return userRole === 'HOME' ? (isTop ? 'PITCHER' : 'BATTER') : isTop ? 'BATTER' : 'PITCHER'
}

interface IntroPlayer {
  name: string
  number: string
  photo?: string
  overall?: number
  position?: string
}

function extractLineupIds(state: GameStateWS | null, userRole: 'HOME' | 'AWAY'): {
  user: string[]
  cpu: string[]
} {
  const data = (state?.state_data ?? {}) as Record<string, unknown>
  const home = Array.isArray(data.home_lineup) ? (data.home_lineup as string[]) : []
  const away = Array.isArray(data.away_lineup) ? (data.away_lineup as string[]) : []
  if (userRole === 'HOME') return { user: home, cpu: away }
  return { user: away, cpu: home }
}

function extractTacticalHand(state: GameStateWS | null, userRole: 'HOME' | 'AWAY'): string[] {
  const data = (state?.state_data ?? {}) as Record<string, unknown>
  const tactics = (data.tactics ?? {}) as Record<string, { hand?: unknown }>
  const key = userRole === 'HOME' ? 'home' : 'away'
  const hand = tactics[key]?.hand
  return Array.isArray(hand) ? (hand as string[]) : []
}

function extractNextBatterId(state: GameStateWS | null): string | null {
  if (!state) return null
  const data = (state.state_data ?? {}) as Record<string, unknown>
  const lineupKey = state.isTopInning ? 'away_lineup' : 'home_lineup'
  const indexKey = state.isTopInning ? 'away_batter_index' : 'home_batter_index'
  const lineup = Array.isArray(data[lineupKey]) ? (data[lineupKey] as string[]) : []
  const currentIndex = typeof data[indexKey] === 'number' ? data[indexKey] : 0

  if (lineup.length === 0) return null
  return lineup[(currentIndex + 1) % lineup.length] ?? null
}

function toIntroPlayer(card: PlayerCard): IntroPlayer {
  return {
    name: card.name,    number: card.number,
    photo: undefined,
    overall: card.overall,
    position: card.position,
  }
}

function rarityClass(rarity: string | undefined): string {
  const base = `rarity-${(rarity ?? 'COMMON').toLowerCase()}`
  return ['rarity-common', 'rarity-bronze', 'rarity-silver', 'rarity-gold', 'rarity-diamond'].includes(
    base,
  )
    ? base
    : 'rarity-common'
}

// ============================================================================
// Main Page
// ============================================================================

export function StadiumPage() {
  const { t } = useTranslation()
  const { gameId = '' } = useParams<{ gameId: string }>()
  const navigate = useNavigate()

  const [userTeamName, setUserTeamName] = useState<string>('MI EQUIPO')
  const [userLineup, setUserLineup] = useState<IntroPlayer[]>([])
  const [cpuLineup, setCpuLineup] = useState<IntroPlayer[]>([])
  const [showIntro, setShowIntro] = useState(() => !isIntroShown(gameId))
  const [resolvedPitcher, setResolvedPitcher] = useState<PlayerGameData | null>(null)
  const [resolvedBatter, setResolvedBatter] = useState<PlayerGameData | null>(null)
  const [resolvedNextBatter, setResolvedNextBatter] = useState<PlayerGameData | null>(null)
  const [selectedZone, setSelectedZone] = useState<number>(5)
  const [pitchSelectorOpen, setPitchSelectorOpen] = useState(false)
  const [selectedTacticalId, setSelectedTacticalId] = useState<string | null>(null)
  const [selectedPitch, setSelectedPitch] = useState<string>('')
  const [hoveredPitchStat, setHoveredPitchStat] = useState<string | null>(null)
  const [hoveredBatterStat, setHoveredBatterStat] = useState<string | null>(null)
  const [showQuit, setShowQuit] = useState(false)
  const [isQuitting, setIsQuitting] = useState(false)
  const [showRivalPitchAck, setShowRivalPitchAck] = useState(false)
  const [showChangePitcher, setShowChangePitcher] = useState(false)
  const [availablePitchers, setAvailablePitchers] = useState<BullpenPitcher[]>([])
  const [isLoadingPitchers, setIsLoadingPitchers] = useState(false)
  const ownPitcherChangeRef = useRef<string | null>(null)
  const [rivalPitchData, setRivalPitchData] = useState<{
    oldPitcher: PlayerGameData | null
    newPitcher: PlayerGameData | null
  } | null>(null)
  const [inningTransition, setInningTransition] = useState<{
    completedInning: number
    completedHalf: 'TOP' | 'BOT'
    nextInning: number
    nextHalf: 'TOP' | 'BOT'
    homeScore: number
    awayScore: number
  } | null>(null)
  const [modalResult, setModalResult] = useState<{
    text: string
    event: string
    ts: number
  } | null>(null)
  const introAudioRef = useRef<HTMLAudioElement | null>(null)

  const { onStep, enqueueEvent } = useEventSequencer()

  // Snapshot del último estado "commiteado" para el deferred display.
  const deferredRef = useRef<GameStateWS | null>(null)

  const { game, isConnected, error, sendPitch, sendSwing, sendChangePitcher, sendAcknowledgePitcherChange } =
    useGameSocket(gameId, {
      onPlayResolved: (payload) => {
        const event = 'event' in payload ? payload.event : ''
        const normalized = normalizeEventName(event)
        enqueueEvent(normalized, payload)
      },
      onPitcherChanged: (payload) => {
        const pd = payload as unknown as {
          old_pitcher_data?: PlayerGameData
          new_pitcher?: PlayerGameData
        }
        if (pd.new_pitcher?.id === ownPitcherChangeRef.current) {
          ownPitcherChangeRef.current = null
          setResolvedPitcher(pd.new_pitcher)
          const currentGame = useGameStore.getState().game
          if (currentGame) {
            useGameStore.getState().setGame({
              ...currentGame,
              activePitcherId: pd.new_pitcher.id,
              active_pitcher: pd.new_pitcher,
              state_data: {
                ...currentGame.state_data,
                ...(payload.state_data ?? {}),
              },
            })
          }
          return
        }
        setRivalPitchData({
          oldPitcher: pd.old_pitcher_data ?? null,
          newPitcher: pd.new_pitcher ?? null,
        })
        setShowRivalPitchAck(true)
      },
    })

  const userRole: 'HOME' | 'AWAY' = game?.userRole ?? 'HOME'
  const isTopInning = game?.isTopInning ?? true
  const role = resolveRole(userRole, isTopInning)

  // Deferred: durante el overlay de resultado mostramos el estado previo.
  const displayedGame = modalResult && deferredRef.current ? deferredRef.current : game

  const livePitcher = game?.active_pitcher
  const activePitcher = useMemo<PlayerGameData | undefined>(() => {
    if (!livePitcher) return resolvedPitcher ?? undefined
    // PLAY_RESOLVED no incluye repertoire; conservar el del pitcher resuelto en el init.
    if (!livePitcher.repertoire && resolvedPitcher?.repertoire) {
      return { ...livePitcher, repertoire: resolvedPitcher.repertoire }
    }
    return livePitcher
  }, [livePitcher, resolvedPitcher])
  const activeBatter = game?.active_batter ?? resolvedBatter ?? undefined

  const pitcher = useMemo(() => toPitcherSummary(activePitcher), [activePitcher])
  const batter = useMemo(() => toBatterSummary(activeBatter), [activeBatter])
  const nextBatterId = extractNextBatterId(game)
  const nextBatter = useMemo(
    () =>
      toBatterSummary(
        resolvedNextBatter?.id === nextBatterId ? resolvedNextBatter : undefined,
      ),
    [nextBatterId, resolvedNextBatter],
  )
  const tacticalHand = useMemo(
    () => extractTacticalHand(game, userRole).slice(0, 3),
    [game, userRole],
  )

  // La partida "arranca" visualmente cuando se cierra el modal de previa,
  // momento en el que el HUD entra desde los laterales.
  const started = !showIntro
  const isIntroVisible = showIntro && Boolean(game)

  useEffect(() => {
    const audio = introAudioRef.current
    if (!audio) return

    if (isIntroVisible) {
      audio.currentTime = 0
      void audio.play().catch(() => {
        // Algunos navegadores bloquean autoplay sin interacción previa.
      })
    } else {
      audio.pause()
      audio.currentTime = 0
    }

    return () => {
      audio.pause()
      audio.currentTime = 0
    }
  }, [isIntroVisible])

  // Cargar nombre del equipo del usuario.
  useEffect(() => {
    getTeam().then((team) => setUserTeamName(team.name)).catch(() => undefined)
  }, [])

  // Resolver lineups (usuario vs CPU) desde los IDs de state_data.
  useEffect(() => {
    if (!game) return
    const { user, cpu } = extractLineupIds(game, userRole)
    if (user.length === 0 && cpu.length === 0) return
    const toIntro = (ids: string[]) =>
      Promise.all(
        ids.slice(0, 9).map((id) =>
          getCard(id)
            .then(toIntroPlayer)
            .catch(() => ({ name: 'Jugador', number: '?', position: 'DH', overall: 0 })),
        ),
      )
    toIntro(user).then(setUserLineup)
    toIntro(cpu).then(setCpuLineup)
  }, [game, userRole])

  // Poblar las tarjetas de pitcher/bateador con datos reales cuando el
  // INIT_GAME_STATE solo provee IDs en state_data (PLAY_RESOLVED sí trae el objeto).
  useEffect(() => {
    if (!game) return
    const data = (game.state_data ?? {}) as Record<string, unknown>
    const pitcherId = typeof data.active_pitcher === 'string' ? data.active_pitcher : undefined
    const batterId = typeof data.active_batter === 'string' ? data.active_batter : undefined
    const pitchCounts =
      typeof data.pitch_counts === 'object' && data.pitch_counts !== null
        ? (data.pitch_counts as Record<string, number>)
        : {}

    if (pitcherId && !game.active_pitcher) {
      getCard(pitcherId)
        .then((card) =>
          setResolvedPitcher({
            ...toGamePlayer(card, 'PITCHER'),
            pitch_count: pitchCounts[pitcherId] ?? 0,
          }),
        )
        .catch(() => undefined)
    }
    if (batterId && !game.active_batter) {
      getCard(batterId)
        .then((card) => setResolvedBatter(toGamePlayer(card, 'BATTER')))
        .catch(() => undefined)
    }
  }, [game])

  // Resolver el jugador que sigue en el orden ofensivo. En la alta batea AWAY
  // y en la baja batea HOME, independientemente de cuál sea el equipo humano.
  useEffect(() => {
    if (!nextBatterId) return

    let active = true
    getCard(nextBatterId)
      .then((card) => {
        if (active) setResolvedNextBatter(toGamePlayer(card, 'BATTER'))
      })
      .catch(() => {
        if (active) setResolvedNextBatter(null)
      })

    return () => {
      active = false
    }
  }, [nextBatterId])

  // Registrar pasos del event sequencer para el overlay de resultado.
  useEffect(() => {
    onStep('show-modal', (payload) => {
      const p = payload as { event?: string; description?: string }
      setModalResult({ text: p.description ?? '', event: p.event ?? '', ts: Date.now() })
    })
    onStep('close-modal', () => setModalResult(null))
    onStep('check-inning-end', (payload) => {
      const p = payload as { inning_completed?: boolean }
      if (!p.inning_completed) return
      const g = useGameStore.getState().game
      if (!g) return
      const nextInning = g.currentInning
      const nextHalf: 'TOP' | 'BOT' = g.isTopInning ? 'TOP' : 'BOT'
      const completedInning = nextHalf === 'BOT' ? nextInning : nextInning - 1
      setInningTransition({
        completedInning: Math.max(1, completedInning),
        completedHalf: nextHalf === 'BOT' ? 'BOT' : 'TOP',
        nextInning,
        nextHalf,
        homeScore: g.homeScore,
        awayScore: g.awayScore,
      })
    })
  }, [onStep])

  // Mantener el snapshot previo: antes de que llegue el nuevo overlay.
  useEffect(() => {
    deferredRef.current = game
  })

  // Auto-limpiar transición de inning cuando llega el siguiente estado en vivo.
  useEffect(() => {
    if (inningTransition && isConnected && !modalResult) {
      const tmr = setTimeout(() => setInningTransition(null), 3200)
      return () => clearTimeout(tmr)
    }
  }, [inningTransition, isConnected, modalResult])

  const handlePlay = () => {
    if (role === 'PITCHER') {
      setPitchSelectorOpen(false)
    }
    if (!game || !displayedGame) return
    if (role === 'PITCHER') {
      const pitchType = selectedPitch || (pitcher.repertoire?.[0]?.pitch_type ?? '4FB')
      void sendPitch(selectedZone, pitchType)
    } else {
      void sendSwing('NORMAL', selectedZone, null)
    }
  }

  const handleZoneSelect = (zone: number) => {
    setSelectedZone(zone)
    if (role === 'PITCHER') setPitchSelectorOpen(true)
  }

  const handleSelectPitch = (pitch: string) => {
    setSelectedPitch(pitch)
    setPitchSelectorOpen(false)
  }

  const handleIBB = () => {
    const zone = selectedZone
    // Tras el boleto intencional, zone y pitcheo vuelven a su estado inicial.
    setSelectedPitch('')
    setPitchSelectorOpen(false)
    setSelectedZone(5)
    void sendPitch(zone, 'IBB')
  }

  const handleReturnToLobby = () => {
    navigate('/lobby')
  }

  const handleQuitConfirm = async () => {
    setIsQuitting(true)
    setTimeout(() => {
      setIsQuitting(false)
      navigate('/lobby')
    }, 700)
  }

  const handleAckPitcherChange = async () => {
    try {
      await sendAcknowledgePitcherChange()
    } finally {
      setShowRivalPitchAck(false)
      setRivalPitchData(null)
    }
  }

  const handleOpenBullpen = async () => {
    if (!gameId || role !== 'PITCHER' || pitcher.pitchCount < 5) return
    setShowChangePitcher(true)
    setIsLoadingPitchers(true)
    try {
      const response = await getAvailablePitchers(gameId)
      setAvailablePitchers(response.available_pitchers ?? [])
    } catch {
      setAvailablePitchers([])
    } finally {
      setIsLoadingPitchers(false)
    }
  }

  const handleChangePitcher = async (newPitcherId: string) => {
    ownPitcherChangeRef.current = newPitcherId
    try {
      await sendChangePitcher(newPitcherId)
    } catch (changeError) {
      ownPitcherChangeRef.current = null
      throw changeError
    }
  }

  const bases = {
    first: Boolean(game?.runners.b1),
    second: Boolean(game?.runners.b2),
    third: Boolean(game?.runners.b3),
  }

  return (
    <div
      className={`${styles.gameBg} relative min-h-screen w-screen bg-cover bg-center bg-koshien-dark lg:h-dvh lg:overflow-hidden`}
    >
      <audio ref={introAudioRef} src="/audio/playball-stadium.mp3" preload="auto" />
      <div className="pointer-events-none absolute inset-0 z-0 bg-black/55" />

      <div className="relative z-10 flex min-h-full flex-col">
        <PlayResultOverlay
          resultText={modalResult?.text ?? null}
          resultEvent={modalResult?.event ?? null}
          resultTs={modalResult?.ts ?? null}
        />

      {showIntro && game && (
        <GameIntroModal
          userTeamName={userTeamName}
          userPitcher={pitcher.id ? { name: pitcher.name, number: pitcher.number, overall: pitcher.overall } : undefined}
          userLineup={userLineup}
          cpuTeamName={game.rivalTeamName ?? 'RIVAL'}
          cpuPitcher={
            activePitcher
              ? { name: activePitcher.name, number: activePitcher.number, overall: activePitcher.overall }
              : undefined
          }
          cpuLineup={cpuLineup}
          onPlayBall={() => {
            markIntroShown(gameId)
            setShowIntro(false)
          }}
        />
      )}

      {inningTransition && (
        <InningTransitionModal
          completedInning={inningTransition.completedInning}
          completedHalf={inningTransition.completedHalf}
          nextInning={inningTransition.nextInning}
          nextHalf={inningTransition.nextHalf}
          homeScore={inningTransition.homeScore}
          awayScore={inningTransition.awayScore}
          userRole={userRole}
        />
      )}

      {game?.isGameOver && (
        <GameOverModal
          winnerMessage={game.winnerMessage}
          homeScore={game.homeScore}
          awayScore={game.awayScore}
          homeTeamName={userTeamName}
          awayTeamName={game.rivalTeamName ?? 'RIVAL'}
          userRole={userRole}
          onReturnToLobby={handleReturnToLobby}
        />
      )}

      <QuitGameModal
        isOpen={showQuit}
        onConfirm={handleQuitConfirm}
        onCancel={() => setShowQuit(false)}
        isLoading={isQuitting}
      />

      <RivalPitcherChangeModal
        isOpen={showRivalPitchAck}
        oldPitcher={rivalPitchData?.oldPitcher ?? null}
        newPitcher={rivalPitchData?.newPitcher ?? null}
        onAccept={handleAckPitcherChange}
      />
      <ChangePitcherModal
        isOpen={showChangePitcher}
        onClose={() => setShowChangePitcher(false)}
        currentPitcher={activePitcher ?? null}
        availablePitchers={availablePitchers}
        onConfirm={handleChangePitcher}
        isLoading={isLoadingPitchers}
      />

      <div className={styles.gameShell}>
        <div className={styles.areaHeader}>
          <motion.div
            initial={{ y: -30, opacity: 0 }}
            animate={started ? { y: 0, opacity: 1 } : {}}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          >
            <Header
              homeTeamName={userTeamName}
              isConnected={isConnected}
              onQuit={() => setShowQuit(true)}
            />
          </motion.div>
        </div>

        {error && (
          <div className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-center font-vintage text-xs uppercase tracking-wider text-red-300">
            {error}
          </div>
        )}

        <div className={styles.scoreRow}>
          <div className={styles.areaScore}>
            <motion.div
              initial={{ x: -120, opacity: 0 }}
              animate={started ? { x: 0, opacity: 1 } : {}}
              transition={{ duration: 0.55, ease: 'easeOut', delay: 0.05 }}
              className="h-full"
            >
              <Scoreboard
                homeTeamName={userTeamName}
                awayTeamName={game?.rivalTeamName ?? 'CPU'}
                homeScore={displayedGame?.homeScore ?? 0}
                awayScore={displayedGame?.awayScore ?? 0}
              />
            </motion.div>
          </div>

          <div className={styles.areaSituation}>
            <motion.div
              initial={{ x: 120, opacity: 0 }}
              animate={started ? { x: 0, opacity: 1 } : {}}
              transition={{ duration: 0.55, ease: 'easeOut', delay: 0.1 }}
              className="h-full"
            >
              <GameSituation
                inning={displayedGame?.currentInning ?? 1}
                isTop={displayedGame?.isTopInning ?? true}
                balls={displayedGame?.balls ?? 0}
                strikes={displayedGame?.strikes ?? 0}
                outs={displayedGame?.outs ?? 0}
                bases={bases}
                role={role}
              />
            </motion.div>
          </div>
        </div>

        <div className={styles.coreGameplay}>
          <div className={styles.areaPitcher}>
            <motion.div
              className={styles.playerCard}
              initial={{ x: -160, opacity: 0 }}
              animate={started ? { x: 0, opacity: 1 } : {}}
              transition={{ duration: 0.6, ease: 'easeOut', delay: 0.12 }}
            >
              <PitcherCard
                pitcher={pitcher}
                role={role}
                hoveredStat={hoveredPitchStat}
                setHoveredStat={setHoveredPitchStat}
                onChangePitcher={handleOpenBullpen}
              />
            </motion.div>
          </div>

          <div className={styles.areaPitcherMeta}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={started ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, ease: 'easeOut', delay: 0.18 }}
              className="h-full w-full"
            >
              <PitcherMetaBar pitcher={pitcher} />
            </motion.div>
          </div>

          <div className={styles.areaZone}>
            <motion.div
              className={styles.strikeZoneBox}
              initial={{ scale: 0.7, opacity: 0, y: 20 }}
              animate={started ? { scale: 1, opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, ease: 'easeOut', delay: 0.2 }}
            >
              <StrikeZone
                selectedZone={selectedZone}
                setSelectedZone={handleZoneSelect}
                selectedPitch={selectedPitch}
                role={role}
                disabled={Boolean(modalResult)}
              />
            </motion.div>

            {role === 'PITCHER' && (
              <div className="mt-1 w-full">
                <button
                  type="button"
                  onClick={handleIBB}
                  className="w-full rounded border border-koshien-gold/50 bg-koshien-dark px-3 py-1.5 font-vintage text-[10px] font-bold uppercase tracking-widest text-koshien-gold transition-colors hover:bg-koshien-gold/10"
                >
                  {t('game.intentional_walk')}
                </button>
              </div>
            )}

            {role === 'BATTER' && (
              <div className="mt-1 hidden w-full desktop:block">
                <div className="neon-amber border border-koshien-border bg-koshien-dark/40 px-3 py-1.5">
                  <div className="text-center font-vintage text-[10px] uppercase text-koshien-gold">
                    {t('game.la_picho')}
                  </div>
                </div>
              </div>
            )}

            {role === 'PITCHER' && pitchSelectorOpen && (
              <motion.div
                className={styles.pitchSelectorFloat}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
              >
                <PitchSelectorPanel
                  repertoire={pitcher.repertoire}
                  selectedPitch={selectedPitch}
                  onSelectPitch={handleSelectPitch}
                  disabled={Boolean(modalResult)}
                />
              </motion.div>
            )}
          </div>

          <div className={styles.areaBatter}>
            <motion.div
              className={styles.playerCard}
              initial={{ x: 160, opacity: 0 }}
              animate={started ? { x: 0, opacity: 1 } : {}}
              transition={{ duration: 0.6, ease: 'easeOut', delay: 0.12 }}
            >
              <BatterCard
                batter={batter}
                role={role}
                hoveredStat={hoveredBatterStat}
                setHoveredStat={setHoveredBatterStat}
              />
            </motion.div>
          </div>

          <div className={styles.areaNext}>
            <motion.div
              initial={{ x: 120, opacity: 0 }}
              animate={started ? { x: 0, opacity: 1 } : {}}
              transition={{ duration: 0.6, ease: 'easeOut', delay: 0.28 }}
              className="w-full"
            >
              <NextBatterPreview nextBatter={nextBatter} />
            </motion.div>
          </div>
        </div>

        {/* Cartas tácticas del lanzador */}
        {role === 'PITCHER' && (
          <div className={styles.actionRow}>
            <div className={styles.areaCards}>
              <motion.div
                initial={{ x: -160, opacity: 0 }}
                animate={started ? { x: 0, opacity: 1 } : {}}
                transition={{ duration: 0.6, ease: 'easeOut', delay: 0.34 }}
              >
                <TacticalCardsArea
                  hand={tacticalHand}
                  selectedTacticalId={selectedTacticalId}
                  disabled={Boolean(modalResult)}
                  onSelect={setSelectedTacticalId}
                />
              </motion.div>
            </div>

            <div className={styles.areaAction}>
              <motion.div
                initial={{ y: 40, opacity: 0 }}
                animate={started ? { y: 0, opacity: 1 } : {}}
                transition={{ duration: 0.55, ease: 'easeOut', delay: 0.42 }}
              >
                <LanzarButton
                  label={t('game.tactic_pitch')}
                  onClick={() => !modalResult && handlePlay()}
                />
              </motion.div>
            </div>
          </div>
        )}

        {role === 'BATTER' && (
          <div className={styles.actionRow}>
            <div className={styles.areaCards}>
              <motion.div
                initial={{ x: -160, opacity: 0 }}
                animate={started ? { x: 0, opacity: 1 } : {}}
                transition={{ duration: 0.6, ease: 'easeOut', delay: 0.34 }}
              >
                <div className="hidden desktop:block">
                  <TacticalCardsArea
                    hand={tacticalHand}
                    selectedTacticalId={selectedTacticalId}
                    disabled={Boolean(modalResult)}
                    onSelect={setSelectedTacticalId}
                  />
                </div>
                <div className="neon-amber border border-koshien-border bg-koshien-dark/40 p-2 desktop:hidden">
                  <div className="text-center font-vintage text-xs uppercase text-koshien-gold sm:text-sm lg:text-[9px]">
                    {t('game.la_picho')}
                  </div>
                </div>
              </motion.div>
            </div>

            <div className={styles.areaAction}>
              <motion.div
                initial={{ y: 40, opacity: 0 }}
                animate={started ? { y: 0, opacity: 1 } : {}}
                transition={{ duration: 0.55, ease: 'easeOut', delay: 0.42 }}
              >
                <LanzarButton
                  label={t('game.tactic_bat')}
                  onClick={() => !modalResult && handlePlay()}
                />
              </motion.div>
            </div>
          </div>
        )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// SECTION COMPONENTS
// ============================================================================

interface HeaderProps {
  homeTeamName: string
  isConnected: boolean
  onQuit: () => void
}

function Header({ homeTeamName, isConnected, onQuit }: HeaderProps) {
  const { t } = useTranslation()
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-2 flex items-center justify-between lg:mb-0"
    >
      <h1 className="font-sports text-2xl font-bold uppercase tracking-wider text-koshien-chalk sm:text-3xl lg:text-2xl">
        {homeTeamName} VS CPU
      </h1>
      <div className="flex items-center gap-3">
        <span
          className={`hidden font-vintage text-[11px] font-bold uppercase tracking-widest sm:inline ${
            isConnected
              ? 'text-[#4ef09a] drop-shadow-[0_0_6px_rgba(78,240,154,0.8)]'
              : 'text-koshien-red'
          }`}
        >
          {isConnected ? t('game.live') : t('game.disconnected')}
        </span>
        <motion.button
          whileHover={{ scale: 1.05, borderColor: '#FF554F' }}
          whileTap={{ scale: 0.95 }}
          onClick={onQuit}
          className="rounded border border-koshien-red bg-koshien-dark px-4 py-2 text-sm font-bold uppercase text-koshien-red transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-red sm:px-6 sm:py-2.5 lg:px-4 lg:py-2 lg:text-xs"
          aria-label="Finalizar partida"
        >
          <span className="text-xs sm:text-sm lg:text-xs">🎬 FINALIZAR</span>
        </motion.button>
      </div>
    </motion.div>
  )
}

interface ScoreboardProps {
  homeTeamName: string
  awayTeamName: string
  homeScore: number
  awayScore: number
}

function Scoreboard({ homeTeamName, awayTeamName, homeScore, awayScore }: ScoreboardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="neon-amber border border-koshien-border bg-koshien-dark/40 p-3 sm:p-4 lg:p-2"
    >
      <div className="mb-2 flex items-center justify-between border-b border-koshien-border/30 pb-2">
        <span className="truncate font-vintage text-[10px] uppercase tracking-widest text-koshien-gold">
          {homeTeamName}
        </span>
        <span className="font-sports text-3xl font-bold text-koshien-chalk lg:text-2xl">
          {homeScore}
        </span>
      </div>
      <div className="mb-2 flex items-center justify-between border-b border-koshien-border/30 pb-2">
        <span className="truncate font-vintage text-[10px] uppercase tracking-widest text-koshien-muted">
          {awayTeamName}
        </span>
        <span className="font-sports text-3xl font-bold text-koshien-chalk lg:text-2xl">
          {awayScore}
        </span>
      </div>

    </motion.div>
  )
}

// ============================================================================
// GAME SITUATION
// ============================================================================

interface GameSituationProps {
  inning: number
  isTop: boolean
  balls: number
  strikes: number
  outs: number
  bases: { first: boolean; second: boolean; third: boolean }
  role: PlayerRole
}

function CountDots({
  total,
  value,
  colorClass,
}: {
  total: number
  value: number
  colorClass: string
}) {
  return (
    <div className={styles.countDots}>
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`${styles.countDot} ${colorClass} ${i < value ? styles.countDotActive : ''}`}
        />
      ))}
    </div>
  )
}

function GameSituation({ inning, isTop, balls, strikes, outs, bases, role }: GameSituationProps) {
  const count = [
    { label: 'BALLS', total: 4, value: balls, colorClass: String(styles.countBalls) },
    { label: 'STRIKES', total: 2, value: strikes, colorClass: String(styles.countStrikes) },
    { label: 'OUTS', total: 2, value: outs, colorClass: String(styles.countOuts) },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className={`${styles.gameSituation} neon-amber border border-koshien-border bg-koshien-dark/40 p-3 sm:p-4`}
    >
      <div className={styles.countRow}>
        {count.map(({ label, total, value, colorClass }) => (
          <div key={label} className="text-center">
            <div className={styles.countLabel}>{label}</div>
            <CountDots total={total} value={value} colorClass={colorClass} />
          </div>
        ))}
      </div>

      <div className={`${styles.situationDivider} ${styles.situationMainDivider}`} />

      <div className={`${styles.situationZone} ${styles.situationInningZone}`}>
        <div className={styles.situationInning}>
          <div className={styles.situationLabel}>INNING</div>
          <div className={styles.situationValue}>{inning}/3</div>
          <div className={styles.situationLabel}>{isTop ? '▲ TOP' : '▼ BOT'}</div>
        </div>
      </div>

      <div className={`${styles.situationDivider} ${styles.situationRowDivider}`} />

      <div className={`${styles.situationZone} ${styles.situationBasesZone}`}>
        <div className={styles.situationLabel} style={{ whiteSpace: 'nowrap', fontSize: '7px', maxWidth: '100px', overflow: 'hidden' }}>{role === 'PITCHER' ? 'TU PICHAS' : 'TU BATEAS'}</div>
        <div className="mt-1 flex justify-center">
          <BasesDiamond bases={bases} />
        </div>
      </div>
    </motion.div>
  )
}

interface BasesDiamondProps {
  bases: { first: boolean; second: boolean; third: boolean }
}

function BasesDiamond({ bases }: BasesDiamondProps) {
  return (
    <svg viewBox="0 0 60 60" className="h-12 w-12 sm:h-14 sm:w-14 lg:h-10 lg:w-10">
      <g className={styles.basesDiamondGraphic}>
        <path d="M 30 10 L 50 30 L 30 50 L 10 30 Z" fill="none" stroke="#F2A13A" strokeWidth="1" />
        <motion.circle
          cx="30"
          cy="10"
          fill={bases.second ? '#F2A13A' : 'none'}
          initial={{ r: 2 }}
          animate={{ r: bases.second ? 3.5 : 2 }}
          transition={{ repeat: bases.second ? Infinity : 0, repeatType: 'reverse', duration: 1 }}
        />
        <motion.circle
          cx="50"
          cy="30"
          fill={bases.first ? '#F2A13A' : 'none'}
          initial={{ r: 2 }}
          animate={{ r: bases.first ? 3.5 : 2 }}
          transition={{
            repeat: bases.first ? Infinity : 0,
            repeatType: 'reverse',
            duration: 1,
            delay: 0.2,
          }}
        />
        <circle cx="30" cy="50" r="2" fill="none" />
        <motion.circle
          cx="10"
          cy="30"
          fill={bases.third ? '#F2A13A' : 'none'}
          initial={{ r: 2 }}
          animate={{ r: bases.third ? 3.5 : 2 }}
          transition={{
            repeat: bases.third ? Infinity : 0,
            repeatType: 'reverse',
            duration: 1,
            delay: 0.1,
          }}
        />
        <circle cx="30" cy="30" r="1.5" fill="#F2A13A" opacity="0.5" />
      </g>
    </svg>
  )
}

// ============================================================================
// PLAYER CARDS (rediseñadas)
// ============================================================================

interface TacticalCardsAreaProps {
  hand: string[]
  selectedTacticalId: string | null
  disabled: boolean
  onSelect: (id: string) => void
}

function TacticalCardsArea({ hand, selectedTacticalId, disabled, onSelect }: TacticalCardsAreaProps) {
  const slots = hand.length > 0 ? hand : new Array(3).fill(null)
  return (
    <div className="flex gap-2">
      {slots.map((id, i) => {
        const isSelected = id != null && selectedTacticalId === id
        return (
          <motion.button
            key={id != null ? `${id}-${i}` : `empty-${i}`}
            type="button"
            disabled={disabled || id == null}
            onClick={() => id != null && onSelect(id)}
            whileHover={id == null ? undefined : { scale: 1.04, y: -2 }}
            whileTap={id == null ? undefined : { scale: 0.96 }}
            className={`relative flex h-32 w-24 flex-col items-center justify-between rounded border p-1.5 text-center shadow-xl transition-all sm:h-36 sm:w-28 lg:h-28 lg:w-20 ${
              id == null
                ? 'border-dashed border-koshien-border bg-koshien-dark/20 opacity-40'
                : isSelected
                  ? 'border-2 border-koshien-gold bg-koshien-green/30 shadow-[0_0_14px_rgba(197,160,89,0.5)]'
                  : 'border border-koshien-gold/50 bg-koshien-dark/70 hover:border-koshien-gold'
            }`}
          >
            {id != null && (
              <>
                <span className="text-xl sm:text-2xl lg:text-lg">🃏</span>
                <span className="font-sports text-xs font-bold uppercase text-koshien-gold sm:text-sm lg:text-[11px]">
                  {id}
                </span>
                <span className="font-vintage text-[8px] uppercase text-koshien-muted">
                  táctica
                </span>
              </>
            )}
          </motion.button>
        )
      })}
    </div>
  )
}

interface PitcherCardProps {
  pitcher: PitcherSummary
  role: PlayerRole
  hoveredStat: string | null
  setHoveredStat: (stat: string | null) => void
  onChangePitcher: () => void
}

function PitcherCard({ pitcher, role, hoveredStat, setHoveredStat, onChangePitcher }: PitcherCardProps) {
  const isPitching = role === 'PITCHER'
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.3 }}
      className={`${rarityClass(pitcher.rarity)} flex flex-col border border-koshien-dark/40 bg-koshien-dark/60 p-2 sm:p-3 lg:p-2`}
    >
      <div className={`${styles.playerCardContent} flex-1`}>
        <div className={`${styles.playerCardHeader} mb-1 flex items-center justify-between border-b border-white/10 pb-1`}>
          <span className="font-vintage text-[9px] uppercase text-koshien-muted sm:text-xs lg:text-[10px] desktop:text-[12px]">
            PITCHER {isPitching ? '●' : ''}
          </span>
          <span className="font-sports text-xs font-bold text-koshien-gold sm:text-sm lg:text-[14px] desktop:text-[18px]">
            {pitcher.overall}
          </span>
        </div>

        <motion.div
          animate={{ scale: 1 }}
          initial={{ scale: 0.8 }}
          className={`${styles.playerIdentity} mb-2 text-center font-sports text-2xl font-bold text-koshien-gold sm:text-3xl lg:text-xl`}
        >
          <span className={styles.playerHash}>
            #
          </span>
          <span className={styles.playerNumber}>{pitcher.number}</span>
        </motion.div>

        <div className={`${styles.playerName} mb-2 truncate text-center font-vintage text-[10px] font-bold uppercase text-koshien-chalk sm:text-xs lg:text-[8px]`}>
          {pitcher.name}
        </div>

        <div className={`${styles.playerStats} mb-2 grid grid-cols-3 gap-1 lg:gap-0.5`}>
          {[
            { label: 'VEL', value: pitcher.velocity },
            { label: 'CTRL', value: pitcher.control },
            { label: 'MOV', value: pitcher.movement },
          ].map(({ label, value }) => (
            <motion.div
              key={label}
              onMouseEnter={() => setHoveredStat(label)}
              onMouseLeave={() => setHoveredStat(null)}
              whileHover={{ scale: 1.05 }}
              className={`rounded border transition-all ${
                hoveredStat === label
                  ? 'neon-green border-koshien-dark/40 bg-koshien-green/10'
                  : 'border-koshien-light-green/40 bg-koshien-dark'
              } p-1 text-center`}
            >
              <div className={`${styles.statLabel} font-vintage text-[8px] uppercase text-koshien-muted sm:text-[9px] lg:text-[7px]`}>
                {label}
              </div>
              <motion.div
                animate={{ scale: hoveredStat === label ? 1.1 : 1 }}
                className={`${styles.statValue} font-sports text-xs font-bold text-koshien-gold sm:text-sm lg:text-[14px]`}
              >
                {value}
              </motion.div>
            </motion.div>
          ))}
        </div>
        {isPitching && (
          <button
            type="button"
            onClick={onChangePitcher}
            disabled={pitcher.pitchCount < 5}
            className="mt-auto hidden w-full items-center justify-center border border-koshien-gold/60 bg-koshien-dark/70 px-2 py-1 font-vintage text-[9px] uppercase tracking-wider text-koshien-gold transition hover:bg-koshien-gold/15 disabled:cursor-not-allowed disabled:border-koshien-muted/30 disabled:text-koshien-muted/50 desktop:flex"
          >
            {pitcher.pitchCount < 5
              ? `${5 - pitcher.pitchCount} lanz. para cambio`
              : 'Cambiar lanzador'}
          </button>
        )}
      </div>
    </motion.div>
  )
}

function PitcherMetaBar({ pitcher }: { pitcher: PitcherSummary }) {
  return (
    <motion.div
      className={`${styles.pitcherMeta} flex flex-col justify-center gap-1 border border-koshien-dark/40 bg-koshien-dark/60 p-2 sm:p-3 lg:p-2`}
    >
      <div className="flex items-center justify-between">
        <span className="font-sports text-[10px] font-bold uppercase tracking-wider text-koshien-gold sm:text-sm lg:text-[9px]">
          STAMINA {pitcher.stamina}%
        </span>
        <span className="font-vintage text-[10px] uppercase text-koshien-cream sm:text-sm lg:text-[9px]">
          ⚾ {pitcher.pitchCount} LANZ.
        </span>
      </div>
      <div className="h-1 w-full overflow-hidden rounded bg-koshien-dark/50 lg:h-[3px]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, Math.max(0, pitcher.stamina))}%` }}
          transition={{ duration: 0.8 }}
          className="h-full bg-gradient-to-r from-koshien-green to-koshien-orange"
        />
      </div>
    </motion.div>
  )
}

interface BatterCardProps {
  batter: BatterSummary
  role: PlayerRole
  hoveredStat: string | null
  setHoveredStat: (stat: string | null) => void
}

function BatterCard({ batter, role, hoveredStat, setHoveredStat }: BatterCardProps) {
  const isBatting = role === 'BATTER'
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.4 }}
      className={`${rarityClass(batter.rarity)} flex flex-col border border-koshien-dark/40 bg-koshien-dark/60 p-2 sm:p-3 lg:p-2`}
    >
      <div className={`${styles.playerCardContent} flex-1`}>
        <div className={`${styles.playerCardHeader} mb-1 flex items-center justify-between border-b border-white/10 pb-1`}>
          <span className="font-vintage text-[9px] uppercase text-koshien-muted sm:text-xs lg:text-[10px] desktop:text-[12px]">
            BATTER {isBatting ? '●' : ''}
          </span>
          <span className="font-sports text-xs font-bold text-koshien-gold sm:text-sm lg:text-[14px] desktop:text-[18px]">
            {batter.overall}
          </span>
        </div>

        <motion.div
          animate={{ scale: 1 }}
          initial={{ scale: 0.8 }}
          className={`${styles.playerIdentity} mb-2 text-center font-sports text-2xl font-bold text-koshien-gold sm:text-3xl lg:text-xl`}
        >
          <span className={styles.playerHash}>
            #
          </span>
          <span className={styles.playerNumber}>{batter.number}</span>
        </motion.div>

        <div className={`${styles.playerName} mb-2 truncate text-center font-vintage text-[10px] font-bold uppercase text-koshien-chalk sm:text-xs lg:text-[8px]`}>
          {batter.name}
        </div>

        <div className={`${styles.playerStats} mb-2 grid grid-cols-3 gap-1 lg:gap-0.5`}>
          {[
            { label: 'CON', value: batter.contact },
            { label: 'PWR', value: batter.power },
            { label: 'SPD', value: batter.speed },
          ].map(({ label, value }) => (
            <motion.div
              key={label}
              onMouseEnter={() => setHoveredStat(label)}
              onMouseLeave={() => setHoveredStat(null)}
              whileHover={{ scale: 1.05 }}
              className={`rounded border transition-all ${
                hoveredStat === label
                  ? 'neon-green border-koshien-dark/40 bg-koshien-green/10'
                  : 'border-koshien-light-green/40 bg-koshien-dark'
              } p-1 text-center`}
            >
              <div className={`${styles.statLabel} font-vintage text-[8px] uppercase text-koshien-muted sm:text-[9px] lg:text-[7px]`}>
                {label}
              </div>
              <motion.div
                animate={{ scale: hoveredStat === label ? 1.1 : 1 }}
                className={`${styles.statValue} font-sports text-xs font-bold text-koshien-gold sm:text-sm lg:text-[14px]`}
              >
                {value}
              </motion.div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}

interface NextBatterPreviewProps {
  nextBatter: BatterSummary
}

function NextBatterPreview({ nextBatter }: NextBatterPreviewProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.45 }}
      className={`${styles.nextBatter} neon-green border-2 border-koshien-light-green bg-koshien-green/20`}
    >
      <div className="flex items-center justify-between">
        <span className="font-vintage text-[9px] font-bold uppercase tracking-wider text-koshien-cream lg:text-[8px] desktop:text-[clamp(0.875rem,2.5dvh,1.5rem)]">
          SIG
        </span>
        <motion.span
          animate={{ x: [0, 2, 0] }}
          transition={{ repeat: Infinity, duration: 1 }}
          className="text-[9px] text-koshien-cream desktop:text-[clamp(0.875rem,2.5dvh,1.5rem)]"
        >
          ▶
        </motion.span>
      </div>

      <div className="flex items-baseline gap-1">
        <span className="font-sports font-bold text-koshien-gold text-sm lg:text-xs desktop:text-[clamp(1.25rem,3dvh,2rem)]">
          #{nextBatter.number}
        </span>
        <span className="truncate font-vintage text-xs font-bold uppercase text-koshien-chalk lg:text-[11px] desktop:text-[clamp(1rem,2.5dvh,1.75rem)]">
          {nextBatter.name}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1">
        {[
          { label: 'C', value: nextBatter.contact },
          { label: 'P', value: nextBatter.power },
          { label: 'V', value: nextBatter.speed },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <div className="font-vintage text-[8px] uppercase text-koshien-chalk/70 lg:text-[7px] desktop:text-[clamp(0.75rem,2dvh,1.25rem)]">
              {label}
            </div>
            <div className="font-sports text-sm font-bold text-koshien-light-green lg:text-xs desktop:text-[clamp(1rem,2.5dvh,1.75rem)]">
              {value}
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

// ============================================================================
// STRIKE ZONE
// ============================================================================

interface StrikeZoneProps {
  selectedZone: number
  setSelectedZone: (zone: number) => void
  selectedPitch?: string
  role: PlayerRole
  disabled: boolean
}

function StrikeZone({
  selectedZone,
  setSelectedZone,
  selectedPitch,
  role,
  disabled,
}: StrikeZoneProps) {
  const zones = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
  ]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.35 }}
      className={`neon-amber border border-koshien-border bg-koshien-dark/60 p-2 sm:p-2 lg:p-1 flex flex-col ${
        disabled ? 'pointer-events-none opacity-40' : ''
      }`}
    >
      <div className="mb-1 sm:mb-2 lg:mb-1 text-center font-vintage text-[10px] uppercase text-koshien-gold sm:text-xs lg:text-[9px]">
        {role === 'PITCHER' ? 'ELIGE ZONA' : 'ZONA DE STRIKE'}
      </div>

      <div className="flex-1 flex items-center justify-center">
        <div className="w-full aspect-square grid grid-cols-3 gap-1 lg:gap-0.5">
          {zones.flat().map((zoneNum) => {
            const isSelected = zoneNum === selectedZone
            const showPitch = role === 'PITCHER' && isSelected && selectedPitch
            return (
              <motion.button
                key={zoneNum}
                onClick={() => setSelectedZone(zoneNum)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                layoutId={`zone-${zoneNum}`}
                className={`zone-ripple rounded border transition-all focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-koshien-gold flex items-center justify-center ${
                  isSelected
                    ? 'border-2 border-koshien-red bg-koshien-red/20 shadow-[0_0_8px_rgba(255,85,79,0.4)]'
                    : 'border zone-border bg-koshien-dark/40 hover:border-koshien-gold/60'
                }`}
              >
                {showPitch ? (
                  <span className="px-0.5 font-sports text-[10px] font-bold leading-tight text-koshien-gold sm:text-xs lg:text-[9px]">
                    {selectedPitch}
                  </span>
                ) : (
                  <span className="font-sports text-xs font-bold text-koshien-chalk sm:text-sm lg:text-[9px]">
                    {isSelected ? '🎯' : ''}
                  </span>
                )}
              </motion.button>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}

// ============================================================================
// LANZAR BUTTON
// ============================================================================

interface LanzarButtonProps {
  label: string
  onClick: () => void
}

function LanzarButton({ label, onClick }: LanzarButtonProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.65 }}
      className="flex flex-col items-center gap-2 lg:gap-1"
    >
      <button
        type="button"
        onClick={onClick}
        className="relative flex min-h-[64px] min-w-[150px] flex-col items-center justify-center rounded border-2 border-koshien-orange bg-koshien-dark/80 text-center font-sports text-2xl font-bold uppercase tracking-wider text-koshien-chalk shadow-[0_0_12px_rgba(242,161,58,0.3)] transition-all hover:shadow-[0_0_16px_rgba(242,161,58,0.5)] hover:bg-koshien-orange/10 active:scale-[0.98] sm:min-h-[78px] sm:min-w-[190px] sm:text-3xl lg:min-h-[56px] lg:min-w-[140px] lg:text-xl">
        <span>{label}</span>
      </button>
    </motion.div>
  )
}
