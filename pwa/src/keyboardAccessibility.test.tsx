import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Franchise } from '@/shared/api/types'
import { FranchiseCarousel } from '@/features/onboarding/components/FranchiseCarousel'

const teams: Franchise[] = [
  { id: 'a', name: 'Águilas', city: 'A', color: '#111', secondary_color: '#222', badge: 'AG', desc: '', ovr: 80, batOvr: 80, pitOvr: 80 },
  { id: 'b', name: 'Búhos', city: 'B', color: '#333', secondary_color: '#444', badge: 'BU', desc: '', ovr: 81, batOvr: 81, pitOvr: 81 },
  { id: 'c', name: 'Cardenales', city: 'C', color: '#555', secondary_color: '#666', badge: 'CA', desc: '', ovr: 82, batOvr: 82, pitOvr: 82 },
]

const source = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8')

describe('keyboard accessibility', () => {
  it('recorre y selecciona el carrusel con flechas, Home y End', () => {
    const onSelect = vi.fn()
    HTMLElement.prototype.scrollIntoView = vi.fn()
    render(<FranchiseCarousel teams={teams} selectedTeamId="a" onSelectTeam={onSelect} />)

    const first = screen.getByRole('option', { name: /Águilas/i })
    const second = screen.getByRole('option', { name: /Búhos/i })
    first.focus()
    fireEvent.keyDown(first, { key: 'ArrowRight' })
    expect(onSelect).toHaveBeenLastCalledWith('b')
    expect(second).toHaveFocus()

    fireEvent.keyDown(second, { key: 'End' })
    expect(onSelect).toHaveBeenLastCalledWith('c')
    expect(screen.getByRole('option', { name: /Cardenales/i })).toHaveFocus()
  })

  it('protege estado seleccionado, foco visible y deshabilitado real', () => {
    const tactical = source('src/features/game/components/tactical/TacticalCardItem.tsx')
    const pitchSelector = source('src/features/game/components/pitch/PitchSelector.tsx')
    const roster = source('src/features/team/pages/RosterSelectionPage.tsx')
    const showcase = source('src/features/cards/components/PlayerCardShowcase.tsx')

    expect(tactical).toMatch(/<button[\s\S]*aria-pressed={isSelected}[\s\S]*disabled={disabled}/)
    expect(pitchSelector).toMatch(/disabled={disabled}[\s\S]*aria-pressed=/)
    expect(roster).toContain('aria-pressed={inLineup}')
    expect(roster).toContain('aria-pressed={isSelected}')
    expect(showcase).toContain("event.key === 'Enter' || event.key === ' '")
    expect([tactical, pitchSelector, roster, showcase].every((contents) => contents.includes('focus-visible:outline-2'))).toBe(true)
  })
})
