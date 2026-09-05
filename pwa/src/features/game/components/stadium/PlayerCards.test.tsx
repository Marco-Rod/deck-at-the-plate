import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PitcherCard } from './PlayerCards'

const pitcher = {
  id: 'p1',
  name: 'Ace',
  number: '42',
  overall: 91,
  velocity: 94,
  control: 88,
  movement: 86,
  stamina: 80,
  pitchCount: 4,
  rarity: 'GOLD',
  repertoire: null,
}

describe('PlayerCards', () => {
  it('keeps pitcher substitution disabled until five pitches', () => {
    const onChangePitcher = vi.fn()
    render(
      <PitcherCard
        pitcher={pitcher}
        role="PITCHER"
        hoveredStat={null}
        setHoveredStat={vi.fn()}
        onChangePitcher={onChangePitcher}
      />,
    )

    const button = screen.getByRole('button', { name: '1 lanz. para cambio' })
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(onChangePitcher).not.toHaveBeenCalled()
  })
})
