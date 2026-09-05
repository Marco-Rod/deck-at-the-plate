import { useEffect, useState } from 'react'
import { OfflineSyncStatus } from '@/offline/OfflineSyncStatus'
import { PwaUpdatePrompt } from '@/offline/PwaUpdatePrompt'

type WindowWithIdleCallback = Window & {
  requestIdleCallback?: (callback: () => void, options?: { timeout: number }) => number
  cancelIdleCallback?: (handle: number) => void
}

export function DeferredPwaRuntime() {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const browserWindow = window as WindowWithIdleCallback
    const showRuntime = () => setReady(true)

    if (browserWindow.requestIdleCallback) {
      const handle = browserWindow.requestIdleCallback(showRuntime, { timeout: 2_000 })
      return () => browserWindow.cancelIdleCallback?.(handle)
    }

    const handle = window.setTimeout(showRuntime, 1_000)
    return () => window.clearTimeout(handle)
  }, [])

  if (!ready) return null

  return (
    <>
      <OfflineSyncStatus />
      <PwaUpdatePrompt />
    </>
  )
}
