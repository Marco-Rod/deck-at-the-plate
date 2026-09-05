import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { StrikeZone } from './StrikeZone'

describe('StrikeZone', () => {
  it('renders nine accessible zones and selects an enabled zone', () => {
    const setSelectedZone = vi.fn()
    render(
      <StrikeZone
        selectedZone={5}
        selectedPitch="SL"
        role="PITCHER"
        disabled={false}
        setSelectedZone={setSelectedZone}
      />,
    )

    expect(screen.getAllByRole('button')).toHaveLength(9)
    expect(screen.getByRole('button', { name: 'Zona 5' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('SL')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Zona 8' }))
    expect(setSelectedZone).toHaveBeenCalledWith(8)
  })

  it('disables every zone when play is locked', () => {
    const { container } = render(
      <StrikeZone selectedZone={1} role="BATTER" disabled setSelectedZone={vi.fn()} />,
    )
    for (const button of within(container).getAllByRole('button')) expect(button).toBeDisabled()
  })
})
