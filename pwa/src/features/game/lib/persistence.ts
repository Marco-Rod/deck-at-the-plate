import type { GameStateWS } from '@/shared/api/types'
import { gameStateKey, offlineDb } from '@/offline/db'

const GAME_STATE_KEY = 'game_state_persistence'
const GAME_METADATA_KEY = 'game_metadata'
const GAME_SESSION_KEY = 'deck_at_plate_active_game'
const INTRO_SHOWN_KEY = 'deck_at_plate_intro_shown'

interface GameMetadata {
  gameId: string
  userId: string
  savedAt: number
  lastInning: number
}

interface GameSessionData {
  gameId: string
  userId: string
  timestamp: number
}

const SENSITIVE_STATE_KEYS = ['current_pitch']

function sanitizePersistedState(stateData: Record<string, unknown>): Record<string, unknown> {
  const sanitized = { ...(stateData ?? {}) }
  for (const key of SENSITIVE_STATE_KEYS) {
    delete sanitized[key]
  }
  return sanitized
}

export async function persistGameState(
  gameState: GameStateWS | null,
  gameId: string,
  userId: string,
): Promise<void> {
  if (!gameState) return
  try {
    const dataToSave: GameStateWS = {
      gameId: gameState.gameId,
      currentInning: gameState.currentInning,
      isTopInning: gameState.isTopInning,
      homeScore: gameState.homeScore,
      awayScore: gameState.awayScore,
      balls: gameState.balls,
      strikes: gameState.strikes,
      outs: gameState.outs,
      runners: gameState.runners,
      activePitcherId: gameState.activePitcherId,
      activeBatterId: gameState.activeBatterId,
      isGameOver: gameState.isGameOver,
      winnerMessage: gameState.winnerMessage,
      rivalTeamName: gameState.rivalTeamName,
      userRole: gameState.userRole,
      pitcher_strikeouts: gameState.pitcher_strikeouts ?? {},
      batter_stats: gameState.batter_stats ?? {},
      homeHits: gameState.homeHits ?? 0,
      awayHits: gameState.awayHits ?? 0,
      inning_runs: gameState.inning_runs ?? {},
      state_data: sanitizePersistedState(gameState.state_data ?? {}),
    }
    await offlineDb.gameState.put({
      key: gameStateKey(gameId, userId),
      gameId,
      userId,
      updatedAt: Date.now(),
      state: dataToSave,
    })
  } catch (err) {
    console.error('[PERSISTENCE] Error guardando gameState:', err)
  }
}

function recoverLegacyGameState(gameId: string, saved: Partial<GameStateWS>): GameStateWS {
  const stateData = saved.state_data ?? {}
  return {
    gameId: saved.gameId ?? gameId,
    currentInning: saved.currentInning ?? 1,
    isTopInning: saved.isTopInning ?? true,
    homeScore: saved.homeScore ?? 0,
    awayScore: saved.awayScore ?? 0,
    balls: saved.balls ?? 0,
    strikes: saved.strikes ?? 0,
    outs: saved.outs ?? 0,
    runners: saved.runners ?? { b1: null, b2: null, b3: null },
    totalInnings:
      typeof stateData.total_innings === 'number' ? stateData.total_innings : 9,
    activePitcherId: saved.activePitcherId,
    activeBatterId: saved.activeBatterId,
    isGameOver: saved.isGameOver,
    winnerMessage: saved.winnerMessage,
    rivalTeamName: saved.rivalTeamName,
    userRole: saved.userRole ?? 'HOME',
    state_data: sanitizePersistedState(stateData),
    pitcher_strikeouts: saved.pitcher_strikeouts ?? {},
    batter_stats: saved.batter_stats ?? {},
    homeHits: saved.homeHits ?? 0,
    awayHits: saved.awayHits ?? 0,
    inning_runs: saved.inning_runs ?? {},
  }
}

async function migrateLegacyGameState(gameId: string, userId: string): Promise<GameStateWS | null> {
  const metadataStr = localStorage.getItem(GAME_METADATA_KEY)
  const savedStr = localStorage.getItem(GAME_STATE_KEY)
  if (!metadataStr || !savedStr) return null

  const metadata = JSON.parse(metadataStr) as GameMetadata
  if (metadata.gameId !== gameId || metadata.userId !== userId) {
    localStorage.removeItem(GAME_STATE_KEY)
    localStorage.removeItem(GAME_METADATA_KEY)
    return null
  }

  const recovered = recoverLegacyGameState(
    gameId,
    JSON.parse(savedStr) as Partial<GameStateWS>,
  )
  await persistGameState(recovered, gameId, userId)
  localStorage.removeItem(GAME_STATE_KEY)
  localStorage.removeItem(GAME_METADATA_KEY)
  return recovered
}

export async function recoverGameState(
  gameId: string,
  userId: string,
): Promise<GameStateWS | null> {
  try {
    const stored = await offlineDb.gameState.get(gameStateKey(gameId, userId))
    if (stored) return stored.state
    return await migrateLegacyGameState(gameId, userId)
  } catch (err) {
    console.error('[PERSISTENCE] Error recuperando gameState:', err)
    return null
  }
}

export async function clearPersistedGameState(): Promise<void> {
  try {
    await offlineDb.gameState.clear()
    localStorage.removeItem(GAME_STATE_KEY)
    localStorage.removeItem(GAME_METADATA_KEY)
  } catch (err) {
    console.error('[PERSISTENCE] Error limpiando gameState:', err)
  }
}

export function saveGameSession(gameId: string, userId: string): void {
  const session: GameSessionData = { gameId, userId, timestamp: Date.now() }
  localStorage.setItem(GAME_SESSION_KEY, JSON.stringify(session))
}

export function getGameSession(): GameSessionData | null {
  try {
    const stored = localStorage.getItem(GAME_SESSION_KEY)
    if (!stored) return null
    return JSON.parse(stored) as GameSessionData
  } catch (err) {
    console.error('[GameRecovery] Error al recuperar sesión:', err)
    return null
  }
}

export function clearGameSession(): void {
  localStorage.removeItem(GAME_SESSION_KEY)
}

/**
 * Persiste que el modal de previa ("Play Ball") ya se mostró para un gameId
 * concreto. Así, al recargar/pedir un partido en curso, el juego salta directo
 * al campo en vez de volver a pedir "Play Ball". Se asocia al gameId para que
 * una partida nueva (otro id) sí vuelva a mostrar la previa.
 */
export function markIntroShown(gameId: string): void {
  try {
    localStorage.setItem(INTRO_SHOWN_KEY, JSON.stringify({ gameId, shown: true }))
  } catch (err) {
    console.error('[PERSISTENCE] Error guardando introShown:', err)
  }
}

/**
 * Indica si la previa ya se mostró para el gameId dado. Devuelve true solo
 * cuando coincide con la partida actual; si es otro gameId (partida nueva),
 * devuelve false para volver a enseñar el modal.
 */
export function isIntroShown(gameId: string): boolean {
  try {
    const raw = localStorage.getItem(INTRO_SHOWN_KEY)
    if (!raw) return false
    const data = JSON.parse(raw) as { gameId?: string; shown?: boolean }
    return data.shown === true && data.gameId === gameId
  } catch (err) {
    console.error('[PERSISTENCE] Error leyendo introShown:', err)
    return false
  }
}
