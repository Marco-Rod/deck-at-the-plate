import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Toast } from '@/shared/ui/Toast'

const source = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8')

describe('live region policy', () => {
  it('anuncia errores de forma urgente y confirmaciones sin interrumpir', () => {
    const { rerender } = render(
      <Toast open tone="error" message="No fue posible guardar" onClose={vi.fn()} />,
    )
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive')

    rerender(<Toast open tone="success" message="Guardado" onClose={vi.fn()} />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite')
  })

  it('protege anuncios únicos para juego, conexión y guardado', () => {
    const result = source('src/features/game/components/modals/PlayResultOverlay.tsx')
    const offline = source('src/offline/OfflineSyncStatus.tsx')
    const stadium = source('src/features/game/pages/StadiumPage.tsx')
    const roster = source('src/features/team/pages/RosterSelectionPage.tsx')
    const team = source('src/features/team/pages/MyTeamPage.tsx')

    expect(result).toMatch(/role="status" aria-live="polite" aria-atomic="true"/)
    expect(result).toContain('<div aria-hidden="true">')
    expect(offline).toContain("role={urgent ? 'alert' : 'status'}")
    expect(offline).toContain("aria-live={urgent ? 'assertive' : 'polite'}")
    expect(stadium).toMatch(/error && \([\s\S]*role="alert"/)
    expect(roster).toMatch(/error \? \([\s\S]*role="alert"/)
    expect(team).toContain("role={savingStatus === 'error' ? 'alert' : 'status'}")
  })
})
