import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { selectIsAuthenticated, useAuthStore } from '@/features/auth/store'

export function ProtectedRoute() {
  const location = useLocation()
  const isAuthenticated = useAuthStore(selectIsAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace state={{ from: location }} />
  }

  return <Outlet />
}
