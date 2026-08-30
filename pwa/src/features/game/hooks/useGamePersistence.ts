import { useEffect } from 'react'
import type { GameStateWS } from '@/shared/api/types'
import {
  clearGameSession,
  clearPersistedGameState,
  getGameSession,
  persistGameState,
  saveGameSession,
} from '@/features/game/lib/persistence'

export function useGamePersistence(
  game: GameStateWS | null,
  gameId: string,
  userId: string | undefined,
  enabled = true,
): void {
  useEffect(() => {
    if (!enabled || !game || !gameId || !userId) return
    if (game.isGameOver) {
      clearPersistedGameState()
      return
    }
    persistGameState(game, gameId, userId)
  }, [game, gameId, userId, enabled])
}

export function useGameSessionRecovery(activeGameId?: string, userId?: string): void {
  const enabled = Boolean(activeGameId && userId)

  useEffect(() => {
    if (!enabled) return
    if (activeGameId && userId) {
      saveGameSession(activeGameId, userId)
    }
    return () => {
      clearGameSession()
    }
  }, [enabled, activeGameId, userId])
}

export function getRecoverableSession() {
  const session = getGameSession()
  if (!session) return null
  const ageMs = Date.now() - session.timestamp
  const maxAgeMs = 60 * 60 * 1000
  if (ageMs >= maxAgeMs) {
    clearGameSession()
    return null
  }
  return session
}