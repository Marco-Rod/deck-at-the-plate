import { create } from 'zustand'
import type { UserTeam } from '@/shared/api/types'
import { getTeam } from './api'

interface TeamState {
  team: UserTeam | null
  error: string | null
  /** true una vez que se intentó cargar el club (independientemente del resultado). */
  hasLoaded: boolean
  loadTeam: () => Promise<UserTeam | null>
  setTeam: (team: UserTeam | null) => void
  reset: () => void
}

export const useTeamStore = create<TeamState>((set, get) => ({
  team: null,
  error: null,
  hasLoaded: false,
  loadTeam: async () => {
    const current = get().team
    if (current) return current

    try {
      const team = await getTeam()
      set({ team, error: null, hasLoaded: true })
      return team
    } catch {
      set({ team: null, error: null, hasLoaded: true })
      return null
    }
  },
  setTeam: (team) => set({ team, error: null, hasLoaded: true }),
  reset: () => set({ team: null, error: null, hasLoaded: false }),
}))

export const selectHasClub = (state: TeamState) => state.team !== null
export const selectTeam = (state: TeamState) => state.team
