import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PlayerStats } from './PlayerStats'

describe('PlayerStats', () => {
  it('renders values and reports hover changes', () => {
    const onHoveredStatChange = vi.fn()
    render(
      <PlayerStats
        stats={[{ label: 'VEL', value: 92 }]}
        hoveredStat={null}
        onHoveredStatChange={onHoveredStatChange}
      />,
    )

    const stat = screen.getByText('VEL').parentElement!
    expect(screen.getByText('92')).toBeInTheDocument()
    fireEvent.mouseEnter(stat)
    fireEvent.mouseLeave(stat)
    expect(onHoveredStatChange).toHaveBeenNthCalledWith(1, 'VEL')
    expect(onHoveredStatChange).toHaveBeenNthCalledWith(2, null)
  })
})
