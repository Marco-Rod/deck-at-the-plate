import { create } from 'zustand'
import type {
  InventoryItem,
  LineupResponse,
  TeamStatsResponse,
} from '@/shared/api/types'
import { useAuthStore } from '@/features/auth/store'
import { saveLineupOfflineFirst } from '@/offline/sync'
import { getInventory, getLineup, getTeamStats } from './api'

interface RosterState {
  inventory: InventoryItem[] | null
  lineup: LineupResponse | null
  stats: TeamStatsResponse | null
  hasLoaded: boolean
  loading: boolean
  error: string | null
  load: () => Promise<void>
  refreshLineup: () => Promise<void>
  updateLineup: (slots: Record<string, string>) => Promise<'saved' | 'queued'>
  reset: () => void
}

export const useRosterStore = create<RosterState>((set, get) => ({
  inventory: null,
  lineup: null,
  stats: null,
  hasLoaded: false,
  loading: false,
  error: null,
  load: async () => {
    if (get().hasLoaded || get().loading) return
    set({ loading: true, error: null })
    try {
      const [inventory, lineup, stats] = await Promise.all([
        getInventory(),
        getLineup(),
        getTeamStats(),
      ])
      set({ inventory: inventory.inventory, lineup, stats, hasLoaded: true, loading: false })
    } catch {
      set({ error: 'No se pudo cargar tu colección.', hasLoaded: true, loading: false })
    }
  },
  updateLineup: async (slots) => {
    const currentLineup = get().lineup
    const payload = { name: currentLineup?.name ?? 'Lineup Principal', slots }
    const userId = useAuthStore.getState().user?.userId
    if (!userId) throw new Error('No hay un usuario autenticado para guardar el lineup.')
    const result = await saveLineupOfflineFirst(userId, payload, currentLineup?.slots ?? {})
    set({ lineup: result.lineup })
    return result.queued ? 'queued' : 'saved'
  },
  refreshLineup: async () => {
    const lineup = await getLineup()
    set({ lineup })
  },
  reset: () =>
    set({ inventory: null, lineup: null, stats: null, hasLoaded: false, loading: false, error: null }),
}))

export const selectInventory = (state: RosterState) => state.inventory
export const selectLineup = (state: RosterState) => state.lineup
export const selectStats = (state: RosterState) => state.stats
