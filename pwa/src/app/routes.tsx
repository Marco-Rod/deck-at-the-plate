import { Navigate } from 'react-router-dom'
import type { RouteObject } from 'react-router-dom'
import { RootLayout } from './RootLayout'
import { ProtectedRoute } from './ProtectedRoute'
import { RootRedirect } from './RootRedirect'
import { AuthPage } from '@/features/auth/pages/AuthPage'
import {
  CardShowcasePage,
  LobbyPage,
  MyTeamPage,
  OnboardingPage,
  RosterSelectionPage,
  StadiumPage,
} from './lazyPages'

export const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    children: [
      { index: true, element: <RootRedirect /> },
      { path: '/auth', element: <AuthPage /> },
      {
        element: <ProtectedRoute />,
        children: [
          { path: '/onboarding', element: <OnboardingPage /> },
          { path: '/lobby', element: <LobbyPage /> },
          { path: '/team', element: <MyTeamPage /> },
          { path: '/roster/:gameId', element: <RosterSelectionPage /> },
          { path: '/showcase', element: <CardShowcasePage /> },
          { path: '/game/:gameId', element: <StadiumPage /> },
        ],
      },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]
