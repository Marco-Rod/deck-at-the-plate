import type { GameStateWS } from '@/shared/api/types'

export function updateBlockReason(
  game: GameStateWS | null,
  pendingMutations: number,
): 'active-game' | 'pending-sync' | null {
  if (game && !game.isGameOver) return 'active-game'
  if (pendingMutations > 0) return 'pending-sync'
  return null
}
