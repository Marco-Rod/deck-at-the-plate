import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LanzarButton, TacticalCardsArea } from './GameActionControls'

describe('GameActionControls', () => {
  it('exposes tactical selection and disabled state', () => {
    const onSelect = vi.fn()
    render(
      <TacticalCardsArea
        hand={['HIT']}
        selectedTacticalId="HIT"
        disabled={false}
        onSelect={onSelect}
      />,
    )
    const card = screen.getByRole('button', { name: /HIT/i })
    expect(card).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(card)
    expect(onSelect).toHaveBeenCalledWith('HIT')
  })

  it('forwards the primary action', () => {
    const onClick = vi.fn()
    render(<LanzarButton label="Lanzar" onClick={onClick} />)
    fireEvent.click(screen.getByRole('button', { name: 'Lanzar' }))
    expect(onClick).toHaveBeenCalledOnce()
  })
})
