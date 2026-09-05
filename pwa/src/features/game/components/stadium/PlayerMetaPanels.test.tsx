import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NextBatterPreview, PitcherMetaBar } from './PlayerMetaPanels'

describe('PlayerMetaPanels', () => {
  it('renders pitcher workload', () => {
    render(<PitcherMetaBar pitcher={{ stamina: 120, pitchCount: 8 }} />)

    expect(screen.getByText('STAMINA 120%')).toBeInTheDocument()
    expect(screen.getByText('⚾ 8 LANZ.')).toBeInTheDocument()
  })

  it('renders the next batter summary', () => {
    render(
      <NextBatterPreview
        nextBatter={{ number: '23', name: 'Marco', contact: 81, power: 77, speed: 68 }}
      />,
    )

    expect(screen.getByText('#23')).toBeInTheDocument()
    expect(screen.getByText('Marco')).toBeInTheDocument()
    expect(screen.getByText('81')).toBeInTheDocument()
  })
})
