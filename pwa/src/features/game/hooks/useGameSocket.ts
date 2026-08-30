import { useCallback, useEffect, useRef } from 'react'
import { gameSocketClient } from '@/features/game/services/socket'
import { useGameStore } from '@/features/game/store'
import {
  clearPersistedGameState,
  persistGameState,
  recoverGameState,
} from '@/features/game/lib/persistence'
import { isPlayResultPayload, parseStateData } from '@/features/game/lib/state'
import { useAuthStore } from '@/features/auth/store'
import * as gameApi from '@/features/game/api'
import type {
  InitGameStatePayload,
  PitcherChangedPayload,
  PlayerRole,
  SwingType,
} from '@/shared/api/types'

export interface GameSocketHandlers {
  onInit?: (payload: InitGameStatePayload) => void
  onPlayResolved?: (payload: Parameters<typeof parseStateData>[0]) => void
  onPitcherChanged?: (payload: PitcherChangedPayload) => void
  onError?: (message: string) => void
}

export function useGameSocket(gameId: string, handlers: GameSocketHandlers = {}) {
  const token = useAuthStore((state) => state.token)
  const userId = useAuthStore((state) => state.user?.userId)
  const handlersRef = useRef(handlers)
  useEffect(() => {
    handlersRef.current = handlers
  }, [handlers])

  const game = useGameStore((state) => state.game)
  const hasPitched = useGameStore((state) => state.hasPitched)
  const isConnected = useGameStore((state) => state.isConnected)
  const connectionMode = useGameStore((state) => state.connectionMode)
  const error = useGameStore((state) => state.error)

  useEffect(() => {
    if (!gameId || !token || !userId) return

    const recovered = recoverGameState(gameId, userId)
    if (recovered) {
      useGameStore.getState().setGame(recovered)
    }

    gameSocketClient.connect(gameId, token, {
      onStatus: (connected, mode) => {
        useGameStore.getState().setConnected(connected)
        useGameStore.getState().setConnectionMode(mode)
      },
      onMessage: (message) => {
        const store = useGameStore.getState()
        switch (message.type) {
          case 'INIT_GAME_STATE': {
            const newState = parseStateData(message)
            store.setGame(newState)
            persistGameState(newState, gameId, userId)
            handlersRef.current.onInit?.(message)
            break
          }
          case 'PITCH_COMMITTED':
            store.setHasPitched(message.has_pitched)
            break
          case 'PLAY_RESOLVED':
          case 'STEAL_RESOLVED': {
            if (isPlayResultPayload(message)) {
              const newState = parseStateData(message)
              store.setGame(newState)
              store.setLastPlayResult(message)
              persistGameState(newState, gameId, userId)
              handlersRef.current.onPlayResolved?.(message)
            }
            break
          }
          case 'PITCHER_CHANGED':
            store.setPitcherChanged(message)
            handlersRef.current.onPitcherChanged?.(message)
            break
          case 'PITCHER_CHANGE_ACKNOWLEDGED':
            store.setPitcherChanged(null)
            break
          case 'ERROR':
            store.setError(message.message)
            handlersRef.current.onError?.(message.message)
            break
        }
      },
    })

    return () => {
      gameSocketClient.disconnect()
    }
  }, [gameId, token, userId])

  useEffect(() => {
    if (game?.isGameOver) {
      clearPersistedGameState()
    }
  }, [game?.isGameOver])

  const sendPitch = useCallback(
    async (zone: number, pitchType: string) => {
      await gameApi.pitch(gameId, { zone, pitch_type: pitchType })
    },
    [gameId],
  )

  const sendSwing = useCallback(
    async (swingType: SwingType, guessedZone: number | null, guessedPitch: string | null) => {
      await gameApi.swing(gameId, {
        swing_type: swingType,
        guessed_zone: guessedZone,
        guessed_pitch: guessedPitch,
      })
    },
    [gameId],
  )

  const sendTactic = useCallback(
    async (tacticId: string, playerRole: PlayerRole) => {
      await gameApi.playTactic(gameId, { player_role: playerRole, tactic_id: tacticId })
    },
    [gameId],
  )

  const sendSteal = useCallback(
    async (targetBase: '2b' | '3b') => {
      await gameApi.steal(gameId, { target_base: targetBase })
    },
    [gameId],
  )

  const sendChangePitcher = useCallback(
    async (newPitcherId: string) => {
      await gameApi.changePitcher(gameId, {
        new_pitcher_id: newPitcherId,
        player_role: 'PITCHER',
      })
    },
    [gameId],
  )

  const sendAcknowledgePitcherChange = useCallback(async () => {
    await gameApi.acknowledgePitcherChange(gameId)
  }, [gameId])

  return {
    game,
    hasPitched,
    isConnected,
    connectionMode,
    error,
    sendPitch,
    sendSwing,
    sendTactic,
    sendSteal,
    sendChangePitcher,
    sendAcknowledgePitcherChange,
  }
}