import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { PageFallback } from '@/shared/ui/PageFallback'

export function RootLayout() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Outlet />
    </Suspense>
  )
}
