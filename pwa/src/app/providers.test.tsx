import { render } from '@testing-library/react'
import { useReducedMotion } from 'framer-motion'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Providers } from './providers'

function ReducedMotionProbe() {
  const shouldReduceMotion = useReducedMotion()
  return <output>{String(shouldReduceMotion)}</output>
}

describe('Providers reduced-motion policy', () => {
  beforeEach(() => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion)',
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
  })

  it('propagates the operating-system preference to Framer Motion', () => {
    const { getByText } = render(
      <Providers>
        <ReducedMotionProbe />
      </Providers>,
    )

    expect(getByText('true')).toBeInTheDocument()
  })
})
