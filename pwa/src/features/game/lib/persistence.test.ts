import { beforeEach, describe, expect, it } from 'vitest'
import { offlineDb } from '@/offline/db'
import type { GameStateWS } from '@/shared/api/types'
import {
  clearPersistedGameState,
  persistGameState,
  recoverGameState,
} from './persistence'

const game: GameStateWS = {
  gameId: 'game-1',
  currentInning: 3,
  isTopInning: false,
  homeScore: 2,
  awayScore: 1,
  balls: 1,
  strikes: 2,
  outs: 1,
  runners: { b1: 'runner-1', b2: null, b3: null },
  userRole: 'AWAY',
  state_data: { total_innings: 6, current_pitch: { pitch_type: 'FF', zone: 5 } },
}

beforeEach(async () => {
  await offlineDb.gameState.clear()
})

describe('game persistence', () => {
  it('debe persistir el estado pesado en IndexedDB sin información secreta', async () => {
    await persistGameState(game, 'game-1', 'user-1')

    expect(localStorage.getItem('game_state_persistence')).toBeNull()
    const recovered = await recoverGameState('game-1', 'user-1')
    expect(recovered?.currentInning).toBe(3)
    expect(recovered?.state_data?.current_pitch).toBeUndefined()
  })

  it('debe aislar estados por partida y usuario', async () => {
    await persistGameState(game, 'game-1', 'user-1')

    expect(await recoverGameState('game-1', 'user-2')).toBeNull()
    expect(await recoverGameState('game-2', 'user-1')).toBeNull()
  })

  it('debe migrar una sesión legacy válida y retirar sus claves antiguas', async () => {
    localStorage.setItem(
      'game_metadata',
      JSON.stringify({ gameId: 'game-1', userId: 'user-1', savedAt: 1, lastInning: 3 }),
    )
    localStorage.setItem('game_state_persistence', JSON.stringify(game))

    const recovered = await recoverGameState('game-1', 'user-1')

    expect(recovered?.userRole).toBe('AWAY')
    expect(recovered?.state_data?.current_pitch).toBeUndefined()
    expect(localStorage.getItem('game_metadata')).toBeNull()
    expect(localStorage.getItem('game_state_persistence')).toBeNull()
    expect(await offlineDb.gameState.count()).toBe(1)
  })

  it('debe limpiar IndexedDB y cualquier residuo legacy', async () => {
    await persistGameState(game, 'game-1', 'user-1')
    localStorage.setItem('game_metadata', '{}')

    await clearPersistedGameState()

    expect(await offlineDb.gameState.count()).toBe(0)
    expect(localStorage.getItem('game_metadata')).toBeNull()
  })
})
