import Dexie, { type EntityTable } from 'dexie'
import type { GameStateWS, InventoryItem, LineupResponse } from '@/shared/api/types'

export const DATABASE_NAME = 'DeckAtThePlate'
export const DATABASE_VERSION = 2

export interface StoredGameState {
  key: string
  gameId: string
  userId: string
  updatedAt: number
  state: GameStateWS
}

export interface StoredGameHistory {
  gameId: string
  userId: string
  finishedAt: number
  summary: Record<string, unknown>
}

export interface StoredUserCards {
  key: string
  userId: string
  cardId: string
  updatedAt: number
  item: InventoryItem
}

export interface StoredRoster {
  key: string
  userId: string
  lineupId: string
  updatedAt: number
  lineup: LineupResponse
}

export type OfflineMutationStatus = 'pending' | 'processing' | 'failed'

export interface StoredOfflineMutation {
  id: string
  userId: string
  operation: string
  dedupeKey: string
  payload: unknown
  createdAt: number
  updatedAt: number
  nextAttemptAt: number
  attempts: number
  maxAttempts: number
  status: OfflineMutationStatus
  lastError?: string
}

export class DeckDatabase extends Dexie {
  gameState!: EntityTable<StoredGameState, 'key'>
  gameHistory!: EntityTable<StoredGameHistory, 'gameId'>
  userCards!: EntityTable<StoredUserCards, 'key'>
  roster!: EntityTable<StoredRoster, 'key'>
  offlineMutations!: EntityTable<StoredOfflineMutation, 'id'>

  constructor(name = DATABASE_NAME) {
    super(name)

    this.version(DATABASE_VERSION).stores({
      gameState: '&key, gameId, userId, [gameId+userId], updatedAt',
      gameHistory: '&gameId, userId, finishedAt, [userId+finishedAt]',
      userCards: '&key, userId, cardId, [userId+cardId], updatedAt',
      roster: '&key, userId, lineupId, [userId+lineupId], updatedAt',
      offlineMutations:
        '&id, userId, operation, dedupeKey, status, nextAttemptAt, [userId+status]',
    })
  }
}

export const offlineDb = new DeckDatabase()

export function gameStateKey(gameId: string, userId: string): string {
  return `${userId}:${gameId}`
}

export function userCardKey(userId: string, cardId: string): string {
  return `${userId}:${cardId}`
}

export function rosterKey(userId: string, lineupId: string): string {
  return `${userId}:${lineupId}`
}
