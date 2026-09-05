import { describe, expect, it } from 'vitest'
import type { GameStateWS } from '@/shared/api/types'
import { updateBlockReason } from './updatePolicy'

const activeGame = {
  gameId: 'game-1',
  currentInning: 1,
  isTopInning: true,
  homeScore: 0,
  awayScore: 0,
  balls: 0,
  strikes: 0,
  outs: 0,
  runners: { b1: null, b2: null, b3: null },
  userRole: 'HOME',
} satisfies GameStateWS

describe('PWA update policy', () => {
  it('bloquea actualizaciones durante una partida activa', () => {
    expect(updateBlockReason(activeGame, 0)).toBe('active-game')
  })

  it('bloquea actualizaciones mientras existen cambios pendientes', () => {
    expect(updateBlockReason(null, 2)).toBe('pending-sync')
  })

  it('permite actualizar cuando el estado persistente está seguro', () => {
    expect(updateBlockReason({ ...activeGame, isGameOver: true }, 0)).toBeNull()
    expect(updateBlockReason(null, 0)).toBeNull()
  })
})
