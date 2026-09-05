import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { GameSituation, Header, Scoreboard } from './GameStatusPanels'

describe('GameStatusPanels', () => {
  it('renders the score and game situation independently from page orchestration', () => {
    const { container } = render(
      <>
        <Scoreboard homeTeamName="Tigres" awayTeamName="Leones" homeScore={3} awayScore={2} />
        <GameSituation
          inning={2}
          isTop
          balls={3}
          strikes={1}
          outs={2}
          bases={{ first: true, second: false, third: true }}
          role="PITCHER"
        />
      </>,
    )

    expect(screen.getByText('Tigres')).toBeInTheDocument()
    expect(screen.getByText('Leones')).toBeInTheDocument()
    expect(screen.getByText('2/3')).toBeInTheDocument()
    expect(screen.getByText('▲ TOP')).toBeInTheDocument()
    expect(screen.getByText('TU PICHAS')).toBeInTheDocument()
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  })

  it('keeps the quit action wired through an explicit callback', () => {
    const onQuit = vi.fn()
    render(<Header homeTeamName="Tigres" isConnected onQuit={onQuit} />)

    fireEvent.click(screen.getByRole('button', { name: 'Finalizar partida' }))

    expect(onQuit).toHaveBeenCalledOnce()
  })
})
