import { useTeamStore } from '@/features/team/store'
import { useRosterStore } from '@/features/team/rosterStore'
import { useLobbyStore } from '@/features/lobby/store'
import { useGameStore } from '@/features/game/store'

/**
 * Limpia todos los stores de datos de sesión (no autenticación) al cerrar
 * sesión o al cambiar de cuenta, para evitar que datos de un usuario anterior
 * (p. ej. el club cargado en useTeamStore) contaminen la sesión de otro.
 */
export function resetSessionStores(): void {
  useTeamStore.getState().reset()
  useRosterStore.getState().reset()
  useLobbyStore.getState().reset()
  useGameStore.getState().resetGame()
}
