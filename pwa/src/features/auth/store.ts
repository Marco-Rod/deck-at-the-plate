import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser, LoginResponse } from '@/shared/api/types'

export interface AuthState {
  token: string | null
  user: AuthUser | null
  signIn: (payload: LoginResponse) => void
  signOut: () => void
}

function toSession(payload: LoginResponse): Pick<AuthState, 'token' | 'user'> {
  return {
    token: payload.access_token,
    user: { userId: payload.user_id, username: payload.username },
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      signIn: (payload) => set(toSession(payload)),
      signOut: () => set({ token: null, user: null }),
    }),
    {
      name: 'deck-atpl-auth',
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
)

export const selectIsAuthenticated = (state: AuthState) =>
  state.token !== null && state.user !== null

export const selectToken = (state: AuthState) => state.token

export const selectUser = (state: AuthState) => state.user
