import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Difficulty, GameMode, PlayerPosition } from '@/shared/api/types'

export interface LobbyConfig {
  rivalId: string
  gameMode: GameMode
  difficulty: Difficulty
  innings: number
  playerPosition: PlayerPosition
}

interface LobbyState {
  config: LobbyConfig
  setConfig: (config: Partial<LobbyConfig>) => void
  reset: () => void
}

const DEFAULT_CONFIG: LobbyConfig = {
  rivalId: '',
  gameMode: 'PVE',
  difficulty: 'EASY',
  innings: 3,
  playerPosition: 'HOME',
}

export const useLobbyStore = create<LobbyState>()(
  persist(
    (set) => ({
      config: DEFAULT_CONFIG,
      setConfig: (config) => set((state) => ({ config: { ...state.config, ...config } })),
      reset: () => set({ config: DEFAULT_CONFIG }),
    }),
    {
      name: 'deck-at-the-plate-lobby',
      partialize: (state) => ({ config: state.config }),
    },
  ),
)

export const selectLobbyConfig = (state: LobbyState) => state.config
