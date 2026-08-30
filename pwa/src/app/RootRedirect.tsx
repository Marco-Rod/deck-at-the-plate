import { Navigate } from 'react-router-dom'
import { selectIsAuthenticated, useAuthStore } from '@/features/auth/store'

export function RootRedirect() {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)

  return <Navigate to={isAuthenticated ? '/lobby' : '/auth'} replace />
}
