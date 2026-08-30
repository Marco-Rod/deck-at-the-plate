import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { PageFallback } from '@/shared/ui/PageFallback'
import {
  selectHasCompletedOnboarding,
  selectIsAuthenticated,
  selectProfileLoaded,
  useAuthStore,
} from '@/features/auth/store'
import { useTeamStore } from '@/features/team/store'

export function ProtectedRoute() {
  const location = useLocation()
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const profileLoaded = useAuthStore(selectProfileLoaded)
  const hasCompletedOnboarding = useAuthStore(selectHasCompletedOnboarding)
  const refreshProfile = useAuthStore((state) => state.refreshProfile)
  const teamLoaded = useTeamStore((state) => state.hasLoaded)
  const loadTeam = useTeamStore((state) => state.loadTeam)

  useEffect(() => {
    if (!isAuthenticated) return
    if (!profileLoaded) void refreshProfile()
    if (!teamLoaded) void loadTeam()
  }, [isAuthenticated, profileLoaded, teamLoaded, refreshProfile, loadTeam])

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace state={{ from: location }} />
  }

  if (!profileLoaded || !teamLoaded) {
    return <PageFallback />
  }

  const onBoardingPath = location.pathname === '/onboarding'

  if (!hasCompletedOnboarding && !onBoardingPath) {
    return <Navigate to="/onboarding" replace />
  }

  if (hasCompletedOnboarding && onBoardingPath) {
    return <Navigate to="/lobby" replace />
  }

  return <Outlet />
}
