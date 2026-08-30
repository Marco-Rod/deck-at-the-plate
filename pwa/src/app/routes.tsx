import { Navigate } from 'react-router-dom'
import type { RouteObject } from 'react-router-dom'
import { RootLayout } from './RootLayout'
import {
  AuthPage,
  CardShowcasePage,
  LobbyPage,
  MyTeamPage,
  RosterSelectionPage,
  StadiumPage,
} from './lazyPages'

export const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    children: [
      { index: true, element: <Navigate to="/auth" replace /> },
      { path: '/auth', element: <AuthPage /> },
      { path: '/lobby', element: <LobbyPage /> },
      { path: '/team', element: <MyTeamPage /> },
      { path: '/roster/:gameId', element: <RosterSelectionPage /> },
      { path: '/showcase', element: <CardShowcasePage /> },
      { path: '/game/:gameId', element: <StadiumPage /> },
      { path: '*', element: <Navigate to="/auth" replace /> },
    ],
  },
]
