import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { registerSW } from 'virtual:pwa-register'
import { useGameStore } from '@/features/game/store'
import { offlineDb } from './db'
import { OFFLINE_QUEUE_CHANGED_EVENT } from './sync'
import { updateBlockReason } from './updatePolicy'

export function PwaUpdatePrompt() {
  const { t } = useTranslation()
  const game = useGameStore((state) => state.game)
  const [needRefresh, setNeedRefresh] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const [pendingMutations, setPendingMutations] = useState(0)
  const registrationRef = useRef<ServiceWorkerRegistration | undefined>(undefined)
  const updateRef = useRef<((reloadPage?: boolean) => Promise<void>) | null>(null)

  const refreshPendingCount = useCallback(async () => {
    const count = await offlineDb.offlineMutations
      .where('status')
      .anyOf('pending', 'processing')
      .count()
    setPendingMutations(count)
  }, [])

  useEffect(() => {
    updateRef.current = registerSW({
      immediate: true,
      onNeedRefresh: () => {
        setDismissed(false)
        setNeedRefresh(true)
      },
      onRegisteredSW: (_url, registration) => {
        registrationRef.current = registration
      },
    })

    const initialize = window.setTimeout(() => void refreshPendingCount(), 0)
    const handleQueueChange = () => void refreshPendingCount()
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        void registrationRef.current?.update().catch(() => undefined)
      }
    }
    window.addEventListener(OFFLINE_QUEUE_CHANGED_EVENT, handleQueueChange)
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      window.clearTimeout(initialize)
      window.removeEventListener(OFFLINE_QUEUE_CHANGED_EVENT, handleQueueChange)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [refreshPendingCount])

  if (!needRefresh || dismissed) return null

  const blockReason = updateBlockReason(game, pendingMutations)
  const explanation =
    blockReason === 'active-game'
      ? t('pwa.update_blocked_game')
      : blockReason === 'pending-sync'
        ? t('pwa.update_blocked_sync')
        : t('pwa.update_ready')

  const applyUpdate = async () => {
    if (blockReason || !updateRef.current) return
    await updateRef.current(true)
  }

  return (
    <aside
      role="status"
      aria-live="polite"
      className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] left-1/2 z-[110] w-[min(92vw,30rem)] -translate-x-1/2 rounded-lg border border-koshien-gold bg-koshien-dark/95 p-4 shadow-scoreboard backdrop-blur"
    >
      <p className="font-sports text-lg uppercase text-koshien-gold">{t('pwa.update_title')}</p>
      <p id="pwa-update-explanation" className="mt-1 font-vintage text-[10px] uppercase leading-relaxed text-koshien-chalk">
        {explanation}
      </p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          disabled={Boolean(blockReason)}
          aria-describedby="pwa-update-explanation"
          onClick={() => void applyUpdate()}
          className="rounded border border-koshien-gold bg-koshien-green px-3 py-2 font-vintage text-[10px] uppercase text-koshien-gold disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t('pwa.update_now')}
        </button>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="rounded border border-white/30 px-3 py-2 font-vintage text-[10px] uppercase text-koshien-chalk hover:bg-white/10"
        >
          {t('pwa.update_later')}
        </button>
      </div>
    </aside>
  )
}
