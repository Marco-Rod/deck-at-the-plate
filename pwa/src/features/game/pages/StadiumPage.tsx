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
import {
  GameSituation,
  Header,
  Scoreboard,
} from '@/features/game/components/stadium/GameStatusPanels'
import {
  NextBatterPreview,
  PitcherMetaBar,
} from '@/features/game/components/stadium/PlayerMetaPanels'
import { BatterCard, PitcherCard } from '@/features/game/components/stadium/PlayerCards'
import {
  LanzarButton,
  TacticalCardsArea,
} from '@/features/game/components/stadium/GameActionControls'
import { StrikeZone } from '@/features/game/components/stadium/StrikeZone'
import {
  extractLineupIds,
  extractNextBatterId,
  extractTacticalHand,
  resolveRole,
  toBatterSummary,
  toGamePlayer,
  toIntroPlayer,
  toPitcherSummary,
  type IntroPlayer,
} from '@/features/game/lib/stadiumData'
import { getAvailablePitchers } from '@/features/game/api'
import type { GameStateWS, PlayerGameData } from '@/shared/api/types'

// ============================================================================
// Helpers
// ============================================================================

interface BullpenPitcher extends PlayerGameData {
  already_used?: boolean
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
  const [deferredGame, setDeferredGame] = useState<GameStateWS | null>(null)
  const introAudioRef = useRef<HTMLAudioElement | null>(null)

  const { onStep, enqueueEvent } = useEventSequencer()

  const {
    game,
    isConnected,
    error,
    sendPitch,
    sendSwing,
    sendChangePitcher,
    sendAcknowledgePitcherChange,
  } = useGameSocket(gameId, {
    onPlayResolved: (payload, previousGame) => {
      setDeferredGame(previousGame)
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
  const displayedGame = modalResult && deferredGame ? deferredGame : game

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
    () => toBatterSummary(resolvedNextBatter?.id === nextBatterId ? resolvedNextBatter : undefined),
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
    getTeam()
      .then((team) => setUserTeamName(team.name))
      .catch(() => undefined)
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
      {isIntroVisible ? (
        <audio ref={introAudioRef} src="/audio/playball-stadium.mp3" preload="auto" />
      ) : null}
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
            userPitcher={
              pitcher.id
                ? { name: pitcher.name, number: pitcher.number, overall: pitcher.overall }
                : undefined
            }
            userLineup={userLineup}
            cpuTeamName={game.rivalTeamName ?? 'RIVAL'}
            cpuPitcher={
              activePitcher
                ? {
                    name: activePitcher.name,
                    number: activePitcher.number,
                    overall: activePitcher.overall,
                  }
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
            <div
              role="alert"
              className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-center font-vintage text-xs uppercase tracking-wider text-red-300"
            >
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
// PLAYER CARDS (rediseñadas)
// ============================================================================

// ============================================================================
// STRIKE ZONE
// ============================================================================

// ============================================================================
// LANZAR BUTTON
// ============================================================================
