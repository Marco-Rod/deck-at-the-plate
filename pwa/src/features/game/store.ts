import { create } from 'zustand'
import type {
  GameConnectionMode,
  GameStateWS,
  PitcherChangedPayload,
  PlayResolvedPayload,
  StealResolvedPayload,
} from '@/shared/api/types'

export type PlayResultEvent = PlayResolvedPayload | StealResolvedPayload

interface GameStoreState {
  game: GameStateWS | null
  hasPitched: boolean
  isConnected: boolean
  connectionMode: GameConnectionMode
  error: string | null
  lastPlayResult: PlayResultEvent | null
  pitcherChanged: PitcherChangedPayload | null
  setGame: (game: GameStateWS) => void
  setHasPitched: (value: boolean) => void
  setConnected: (value: boolean) => void
  setConnectionMode: (mode: GameConnectionMode) => void
  setError: (message: string | null) => void
  setLastPlayResult: (payload: PlayResultEvent | null) => void
  setPitcherChanged: (payload: PitcherChangedPayload | null) => void
  resetGame: () => void
}

export const useGameStore = create<GameStoreState>((set) => ({
  game: null,
  hasPitched: false,
  isConnected: false,
  connectionMode: 'ws',
  error: null,
  lastPlayResult: null,
  pitcherChanged: null,
  setGame: (game) => set({ game, error: null }),
  setHasPitched: (hasPitched) => set({ hasPitched }),
  setConnected: (isConnected) => set({ isConnected }),
  setConnectionMode: (connectionMode) => set({ connectionMode }),
  setError: (error) => set({ error }),
  setLastPlayResult: (lastPlayResult) => set({ lastPlayResult }),
  setPitcherChanged: (pitcherChanged) => set({ pitcherChanged }),
  resetGame: () =>
    set({
      game: null,
      hasPitched: false,
      isConnected: false,
      connectionMode: 'ws',
      error: null,
      lastPlayResult: null,
      pitcherChanged: null,
    }),
}))