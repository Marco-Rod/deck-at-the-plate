import { lazy } from 'react'

export const AuthPage = lazy(() =>
  import('../features/auth/pages/AuthPage').then((m) => ({ default: m.AuthPage })),
)
export const OnboardingPage = lazy(() =>
  import('../features/onboarding/pages/OnboardingPage').then((m) => ({
    default: m.OnboardingPage,
  })),
)
export const LobbyPage = lazy(() =>
  import('../features/lobby/pages/LobbyPage').then((m) => ({ default: m.LobbyPage })),
)
export const MyTeamPage = lazy(() =>
  import('../features/team/pages/MyTeamPage').then((m) => ({ default: m.MyTeamPage })),
)
export const RosterSelectionPage = lazy(() =>
  import('../features/team/pages/RosterSelectionPage').then((m) => ({
    default: m.RosterSelectionPage,
  })),
)
export const CardShowcasePage = lazy(() =>
  import('../features/cards/pages/CardShowcasePage').then((m) => ({
    default: m.CardShowcasePage,
  })),
)
export const StadiumPage = lazy(() =>
  import('../features/game/pages/StadiumPage').then((m) => ({ default: m.StadiumPage })),
)
