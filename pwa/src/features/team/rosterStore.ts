import { create } from 'zustand'
import type {
  InventoryItem,
  LineupResponse,
  TeamStatsResponse,
} from '@/shared/api/types'
import { getInventory, getLineup, getTeamStats, saveLineup } from './api'

interface RosterState {
  inventory: InventoryItem[] | null
  lineup: LineupResponse | null
  stats: TeamStatsResponse | null
  hasLoaded: boolean
  loading: boolean
  error: string | null
  load: () => Promise<void>
  updateLineup: (slots: Record<string, string>) => Promise<void>
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
    const payload = { name: get().lineup?.name ?? 'Lineup Principal', slots }
    const saved = await saveLineup(payload)
    set({ lineup: saved })
  },
  reset: () =>
    set({ inventory: null, lineup: null, stats: null, hasLoaded: false, loading: false, error: null }),
}))

export const selectInventory = (state: RosterState) => state.inventory
export const selectLineup = (state: RosterState) => state.lineup
export const selectStats = (state: RosterState) => state.stats
