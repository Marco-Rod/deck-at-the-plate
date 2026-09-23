import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NextBatterPreview, PitcherMetaBar } from './PlayerMetaPanels'

describe('PlayerMetaPanels', () => {
  it('renders pitcher workload as legacy fallback when no fatigue signal', () => {
    render(<PitcherMetaBar pitcher={{ stamina: 120, fatigueBand: null, pitchCount: 8 }} />)

    expect(screen.getByText('STAMINA 120%')).toBeInTheDocument()
    expect(screen.getByText('⚾ 8 LANZ.')).toBeInTheDocument()
  })

  it('renders the fatigue band as the primary text when signal present', () => {
    render(<PitcherMetaBar pitcher={{ stamina: 77, fatigueBand: 'FATIGUED', pitchCount: 32 }} />)

    expect(screen.getByText('STAMINA Fatigued')).toBeInTheDocument()
    expect(screen.getByText('⚾ 32 LANZ.')).toBeInTheDocument()
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
