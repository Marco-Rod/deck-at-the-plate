import type { GameStateWS } from '@/shared/api/types'

const GAME_STATE_KEY = 'game_state_persistence'
const GAME_METADATA_KEY = 'game_metadata'
const GAME_SESSION_KEY = 'deck_at_plate_active_game'

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

export function persistGameState(
  gameState: GameStateWS | null,
  gameId: string,
  userId: string,
): void {
  if (!gameState) return
  try {
    const dataToSave = {
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
    localStorage.setItem(GAME_STATE_KEY, JSON.stringify(dataToSave))
    const metadata: GameMetadata = {
      gameId,
      userId,
      savedAt: Date.now(),
      lastInning: gameState.currentInning,
    }
    localStorage.setItem(GAME_METADATA_KEY, JSON.stringify(metadata))
  } catch (err) {
    console.error('[PERSISTENCE] Error guardando gameState:', err)
  }
}

export function recoverGameState(gameId: string, userId: string): GameStateWS | null {
  try {
    const metadataStr = localStorage.getItem(GAME_METADATA_KEY)
    if (!metadataStr) return null
    const metadata: GameMetadata = JSON.parse(metadataStr)
    if (metadata.gameId !== gameId || metadata.userId !== userId) {
      clearPersistedGameState()
      return null
    }
    const savedStr = localStorage.getItem(GAME_STATE_KEY)
    if (!savedStr) return null
    const saved = JSON.parse(savedStr)
    const recovered: GameStateWS = {
      gameId: saved.gameId ?? gameId,
      currentInning: saved.currentInning,
      isTopInning: saved.isTopInning,
      homeScore: saved.homeScore,
      awayScore: saved.awayScore,
      balls: saved.balls,
      strikes: saved.strikes,
      outs: saved.outs,
      runners: saved.runners,
      totalInnings: saved.state_data?.total_innings ?? 9,
      activePitcherId: saved.activePitcherId,
      activeBatterId: saved.activeBatterId,
      isGameOver: saved.isGameOver,
      winnerMessage: saved.winnerMessage,
      rivalTeamName: saved.rivalTeamName,
      userRole: saved.userRole ?? 'HOME',
      state_data: saved.state_data,
      pitcher_strikeouts: saved.pitcher_strikeouts ?? {},
      batter_stats: saved.batter_stats ?? {},
      homeHits: saved.homeHits ?? 0,
      awayHits: saved.awayHits ?? 0,
      inning_runs: saved.inning_runs ?? {},
    }
    return recovered
  } catch (err) {
    console.error('[PERSISTENCE] Error recuperando gameState:', err)
    clearPersistedGameState()
    return null
  }
}

export function clearPersistedGameState(): void {
  try {
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