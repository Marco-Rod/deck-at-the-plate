import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'

const PRODUCT_NAME = 'Deck at the Plate'

export function getRouteTitleKey(pathname: string): string | null {
  if (pathname === '/auth') return 'meta.auth'
  if (pathname === '/onboarding') return 'meta.onboarding'
  if (pathname === '/lobby') return 'meta.lobby'
  if (pathname === '/team') return 'meta.team'
  if (pathname === '/showcase') return 'meta.showcase'
  if (pathname === '/roster' || pathname.startsWith('/roster/')) return 'meta.roster'
  if (pathname === '/game' || pathname.startsWith('/game/')) return 'meta.game'
  return null
}

export function useRouteMetadata() {
  const { pathname } = useLocation()
  const { t, i18n } = useTranslation()
  const language = (i18n.resolvedLanguage ?? i18n.language ?? 'es').split('-')[0] || 'es'

  useEffect(() => {
    const titleKey = getRouteTitleKey(pathname)
    document.title = titleKey ? `${t(titleKey)} | ${PRODUCT_NAME}` : PRODUCT_NAME
    document.documentElement.lang = language
  }, [language, pathname, t])
}
