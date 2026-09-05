import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { PageFallback } from '@/shared/ui/PageFallback'
import { PwaInstallPrompt } from '@/offline/PwaInstallPrompt'
import { useRouteMetadata } from './useRouteMetadata'

export function RootLayout() {
  useRouteMetadata()

  return (
    <Suspense fallback={<PageFallback />}>
      <Outlet />
      <PwaInstallPrompt />
    </Suspense>
  )
}
