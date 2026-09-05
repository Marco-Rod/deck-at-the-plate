import { lazy, Suspense } from 'react'
import type { ReactNode } from 'react'
import { MotionConfig } from 'framer-motion'
import '@/shared/lib/i18n'

const DeferredPwaRuntime = lazy(() =>
  import('./DeferredPwaRuntime').then((module) => ({ default: module.DeferredPwaRuntime })),
)

export function Providers({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      {children}
      <Suspense fallback={null}>
        <DeferredPwaRuntime />
      </Suspense>
    </MotionConfig>
  )
}
