import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { useGameStore } from '@/features/game/store'
import {
  canSuggestInstall,
  isIosSafari,
  isStandaloneDisplay,
  type NavigatorWithStandalone,
} from './installPolicy'

const INSTALL_DISMISSED_KEY = 'deck-pwa-install-dismissed'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
}

function installedDisplayMode(): boolean {
  const mediaMatches =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(display-mode: standalone)').matches
  return isStandaloneDisplay(navigator as NavigatorWithStandalone, mediaMatches)
}

export function PwaInstallPrompt() {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const activeGame = useGameStore((state) => Boolean(state.game && !state.game.isGameOver))
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null)
  const [installed, setInstalled] = useState(installedDisplayMode)
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(INSTALL_DISMISSED_KEY) === 'true',
  )
  const iosSafari = isIosSafari(navigator)

  useEffect(() => {
    const handleInstallPrompt = (event: Event) => {
      event.preventDefault()
      setInstallEvent(event as BeforeInstallPromptEvent)
    }
    const handleInstalled = () => {
      setInstalled(true)
      setInstallEvent(null)
      localStorage.removeItem(INSTALL_DISMISSED_KEY)
    }
    window.addEventListener('beforeinstallprompt', handleInstallPrompt)
    window.addEventListener('appinstalled', handleInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', handleInstallPrompt)
      window.removeEventListener('appinstalled', handleInstalled)
    }
  }, [])

  const dismiss = () => {
    setDismissed(true)
    localStorage.setItem(INSTALL_DISMISSED_KEY, 'true')
  }

  const install = async () => {
    if (!installEvent) return
    await installEvent.prompt()
    const choice = await installEvent.userChoice
    setInstallEvent(null)
    if (choice.outcome === 'accepted') setInstalled(true)
  }

  const canOfferNativeInstall = installEvent !== null
  if (
    installed ||
    dismissed ||
    !canSuggestInstall(pathname, activeGame) ||
    (!canOfferNativeInstall && !iosSafari)
  ) {
    return null
  }

  return (
    <aside
      role="complementary"
      aria-labelledby="pwa-install-title"
      className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] left-1/2 z-[105] w-[min(92vw,28rem)] -translate-x-1/2 rounded-lg border border-koshien-gold/70 bg-koshien-dark/95 p-4 shadow-scoreboard backdrop-blur"
    >
      <p id="pwa-install-title" className="font-sports text-lg uppercase text-koshien-gold">
        {t('pwa.install_title')}
      </p>
      <p className="mt-1 font-vintage text-[10px] uppercase leading-relaxed text-koshien-chalk">
        {iosSafari ? t('pwa.install_ios') : t('pwa.install_description')}
      </p>
      <div className="mt-3 flex gap-2">
        {canOfferNativeInstall ? (
          <button
            type="button"
            onClick={() => void install()}
            className="rounded border border-koshien-gold bg-koshien-green px-3 py-2 font-vintage text-[10px] uppercase text-koshien-gold"
          >
            {t('pwa.install_action')}
          </button>
        ) : null}
        <button
          type="button"
          onClick={dismiss}
          className="rounded border border-white/30 px-3 py-2 font-vintage text-[10px] uppercase text-koshien-chalk hover:bg-white/10"
        >
          {t('pwa.install_dismiss')}
        </button>
      </div>
    </aside>
  )
}
