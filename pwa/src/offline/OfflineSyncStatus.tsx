import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { useRosterStore } from '@/features/team/rosterStore'
import { offlineDb } from './db'
import { discardMutation, retryFailedMutation } from './mutationQueue'
import { OFFLINE_QUEUE_CHANGED_EVENT, syncOfflineMutations } from './sync'

interface QueueCounts {
  pending: number
  failed: number
}

export function OfflineSyncStatus() {
  const { t } = useTranslation()
  const user = useAuthStore(selectUser)
  const [online, setOnline] = useState(() => navigator.onLine)
  const [reconnected, setReconnected] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [counts, setCounts] = useState<QueueCounts>({ pending: 0, failed: 0 })
  const reconnectTimer = useRef<number | undefined>(undefined)

  const refresh = useCallback(async () => {
    if (!user) {
      setCounts({ pending: 0, failed: 0 })
      return
    }
    const mutations = await offlineDb.offlineMutations.where('userId').equals(user.userId).toArray()
    setCounts({
      pending: mutations.filter((item) => item.status !== 'failed').length,
      failed: mutations.filter((item) => item.status === 'failed').length,
    })
  }, [user])

  const synchronize = useCallback(async () => {
    if (!user || !navigator.onLine) return
    setSyncing(true)
    try {
      const result = await syncOfflineMutations(user.userId)
      if (result.succeeded > 0 || result.failed > 0) {
        await useRosterStore.getState().refreshLineup()
      }
    } finally {
      setSyncing(false)
      await refresh()
    }
  }, [refresh, user])

  useEffect(() => {
    const initialize = window.setTimeout(() => {
      void refresh()
      if (navigator.onLine) void synchronize()
    }, 0)
    const handleOffline = () => {
      setOnline(false)
      setReconnected(false)
    }
    const handleOnline = () => {
      setOnline(true)
      setReconnected(true)
      if (reconnectTimer.current !== undefined) window.clearTimeout(reconnectTimer.current)
      reconnectTimer.current = window.setTimeout(() => setReconnected(false), 3_000)
      void synchronize()
    }
    const handleQueueChange = () => void refresh()
    window.addEventListener('offline', handleOffline)
    window.addEventListener('online', handleOnline)
    window.addEventListener(OFFLINE_QUEUE_CHANGED_EVENT, handleQueueChange)
    return () => {
      window.clearTimeout(initialize)
      if (reconnectTimer.current !== undefined) window.clearTimeout(reconnectTimer.current)
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener(OFFLINE_QUEUE_CHANGED_EVENT, handleQueueChange)
    }
  }, [refresh, synchronize])

  useEffect(() => {
    if (!online || syncing || counts.pending === 0 || !user) return

    let cancelled = false
    let retryTimer: number | undefined
    void offlineDb.offlineMutations
      .where('userId')
      .equals(user.userId)
      .and((item) => item.status === 'pending')
      .toArray()
      .then((pending) => {
        if (cancelled || pending.length === 0) return
        const nextAttemptAt = Math.min(...pending.map((item) => item.nextAttemptAt))
        retryTimer = window.setTimeout(
          () => void synchronize(),
          Math.max(0, nextAttemptAt - Date.now()),
        )
      })

    return () => {
      cancelled = true
      if (retryTimer !== undefined) window.clearTimeout(retryTimer)
    }
  }, [counts.pending, online, syncing, synchronize, user])

  const retryFailed = async () => {
    if (!user) return
    const failed = await offlineDb.offlineMutations
      .where('userId')
      .equals(user.userId)
      .and((item) => item.status === 'failed')
      .toArray()
    await Promise.all(failed.map((item) => retryFailedMutation(item.id)))
    await synchronize()
  }

  const discardFailed = async () => {
    if (!user) return
    const failed = await offlineDb.offlineMutations
      .where('userId')
      .equals(user.userId)
      .and((item) => item.status === 'failed')
      .toArray()
    await Promise.all(failed.map((item) => discardMutation(item.id)))
    await refresh()
  }

  if (online && counts.pending === 0 && counts.failed === 0 && !syncing && !reconnected) return null

  const message = !online
    ? t('offline.disconnected', { count: counts.pending })
    : syncing
      ? t('offline.syncing')
      : counts.failed > 0
        ? t('offline.failed', { count: counts.failed })
        : counts.pending > 0
          ? t('offline.pending', { count: counts.pending })
          : t('offline.reconnected')
  const urgent = !online || counts.failed > 0

  return (
    <aside
      role={urgent ? 'alert' : 'status'}
      aria-live={urgent ? 'assertive' : 'polite'}
      aria-atomic="true"
      className="fixed left-1/2 top-[max(0.75rem,env(safe-area-inset-top))] z-[100] flex -translate-x-1/2 items-center gap-3 rounded-lg border border-amber-400/70 bg-koshien-dark/95 px-4 py-2 shadow-lg backdrop-blur"
    >
      <span className="font-vintage text-[10px] uppercase tracking-widest text-amber-200">
        {message}
      </span>
      {counts.failed > 0 && online ? (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void retryFailed()}
            className="rounded border border-koshien-gold px-2 py-1 font-vintage text-[9px] uppercase text-koshien-gold hover:bg-koshien-green"
          >
            {t('offline.retry')}
          </button>
          <button
            type="button"
            onClick={() => void discardFailed()}
            className="rounded border border-white/30 px-2 py-1 font-vintage text-[9px] uppercase text-koshien-chalk hover:bg-white/10"
          >
            {t('offline.discard')}
          </button>
        </div>
      ) : null}
    </aside>
  )
}
