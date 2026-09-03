import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser, LoginResponse } from '@/shared/api/types'
import { getProfile } from './api'

export interface AuthState {
  token: string | null
  user: AuthUser | null
  /** true una vez que se intentó cargar el perfil (éxito o error). */
  profileLoaded: boolean
  signIn: (payload: LoginResponse) => void
  signOut: () => void
  setOnboardingComplete: (completed: boolean) => void
  refreshProfile: () => Promise<boolean>
}

function toSession(payload: LoginResponse): Pick<AuthState, 'token' | 'user'> {
  return {
    token: payload.access_token,
    user: {
      userId: payload.user_id,
      username: payload.username,
      hasCompletedOnboarding: false,
    },
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      profileLoaded: false,
      signIn: (payload) => set({ ...toSession(payload), profileLoaded: false }),
      signOut: () => {
        set({ token: null, user: null, profileLoaded: false })
        void import('@/shared/lib/sessionCleanup').then(({ resetSessionStores }) =>
          resetSessionStores(),
        )
      },
      setOnboardingComplete: (completed) =>
        set((state) =>
          state.user ? { user: { ...state.user, hasCompletedOnboarding: completed } } : {},
        ),
      refreshProfile: async () => {
        try {
          const profile = await getProfile()
          const completed = Boolean(profile.has_completed_onboarding)
          set((state) => ({
            profileLoaded: true,
            user: state.user ? { ...state.user, hasCompletedOnboarding: completed } : null,
          }))
          return completed
        } catch {
          set({ profileLoaded: true })
          return Boolean(get().user?.hasCompletedOnboarding)
        }
      },
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

export const selectHasCompletedOnboarding = (state: AuthState) =>
  Boolean(state.user?.hasCompletedOnboarding)

export const selectProfileLoaded = (state: AuthState) => state.profileLoaded
