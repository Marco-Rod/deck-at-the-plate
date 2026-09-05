import { afterEach, describe, expect, it } from 'vitest'
import type { GameStateWS, InventoryItem, LineupResponse } from '@/shared/api/types'
import {
  DATABASE_VERSION,
  DeckDatabase,
  gameStateKey,
  rosterKey,
  userCardKey,
} from './db'

const databases: DeckDatabase[] = []

function createDatabase(): DeckDatabase {
  const database = new DeckDatabase(`DeckAtThePlateTest-${crypto.randomUUID()}`)
  databases.push(database)
  return database
}

afterEach(async () => {
  await Promise.all(databases.splice(0).map((database) => database.delete()))
})

describe('offline database', () => {
  it('debe crear el esquema mínimo con una versión explícita', async () => {
    const database = createDatabase()
    await database.open()

    expect(database.verno).toBe(DATABASE_VERSION)
    expect(database.tables.map((table) => table.name).sort()).toEqual([
      'gameHistory',
      'gameState',
      'offlineMutations',
      'roster',
      'userCards',
    ])
  })

  it('debe guardar y recuperar el estado de una partida por usuario', async () => {
    const database = createDatabase()
    const state: GameStateWS = {
      gameId: 'game-1',
      currentInning: 2,
      isTopInning: true,
      homeScore: 1,
      awayScore: 0,
      balls: 0,
      strikes: 1,
      outs: 2,
      runners: { b1: null, b2: 'runner-2', b3: null },
      userRole: 'HOME',
    }

    await database.gameState.put({
      key: gameStateKey(state.gameId, 'user-1'),
      gameId: state.gameId,
      userId: 'user-1',
      updatedAt: 1_788_470_400_000,
      state,
    })

    const stored = await database.gameState.get(gameStateKey('game-1', 'user-1'))
    expect(stored?.state).toEqual(state)
  })

  it('debe persistir historial, inventario y roster sin datos de autenticación', async () => {
    const database = createDatabase()
    const item = {
      card: { id: 'card-1' },
    } as InventoryItem
    const lineup = {
      user_id: 'user-1',
      name: 'Principal',
      slots: { P: 'card-1' },
    } satisfies LineupResponse

    await database.transaction(
      'rw',
      database.gameHistory,
      database.userCards,
      database.roster,
      async () => {
        await database.gameHistory.put({
          gameId: 'game-1',
          userId: 'user-1',
          finishedAt: 1_788_470_400_000,
          summary: { result: 'WIN' },
        })
        await database.userCards.put({
          key: userCardKey('user-1', 'card-1'),
          userId: 'user-1',
          cardId: 'card-1',
          updatedAt: 1_788_470_400_000,
          item,
        })
        await database.roster.put({
          key: rosterKey('user-1', 'lineup-1'),
          userId: 'user-1',
          lineupId: 'lineup-1',
          updatedAt: 1_788_470_400_000,
          lineup,
        })
      },
    )

    expect(await database.gameHistory.count()).toBe(1)
    expect(await database.userCards.count()).toBe(1)
    expect(await database.roster.count()).toBe(1)
    expect(database.tables.some((table) => /auth|token|credential/i.test(table.name))).toBe(false)
  })
})
