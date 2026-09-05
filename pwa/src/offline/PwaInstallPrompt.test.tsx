import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import '@/shared/lib/i18n'
import { useGameStore } from '@/features/game/store'
import { PwaInstallPrompt } from './PwaInstallPrompt'

function renderPrompt(path = '/lobby') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <PwaInstallPrompt />
    </MemoryRouter>,
  )
}

function dispatchInstallPrompt(outcome: 'accepted' | 'dismissed' = 'accepted') {
  const event = new Event('beforeinstallprompt', { cancelable: true })
  const prompt = vi.fn().mockResolvedValue(undefined)
  Object.assign(event, {
    prompt,
    userChoice: Promise.resolve({ outcome, platform: 'web' }),
  })
  act(() => window.dispatchEvent(event))
  return { event, prompt }
}

beforeEach(() => {
  localStorage.removeItem('deck-pwa-install-dismissed')
  useGameStore.getState().resetGame()
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: vi.fn().mockReturnValue({ matches: false }),
  })
})

afterEach(() => {
  cleanup()
  localStorage.removeItem('deck-pwa-install-dismissed')
})

describe('PwaInstallPrompt', () => {
  it('usa el prompt nativo y desaparece después de aceptar', async () => {
    renderPrompt()
    const { event, prompt } = dispatchInstallPrompt()

    expect(event.defaultPrevented).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: /^instalar$/i }))
    await waitFor(() => expect(prompt).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(screen.queryByText(/instala deck/i)).not.toBeInTheDocument())
  })

  it('recuerda cuando el usuario descarta la sugerencia', () => {
    const first = renderPrompt()
    dispatchInstallPrompt('dismissed')
    fireEvent.click(screen.getByRole('button', { name: /ahora no/i }))
    expect(localStorage.getItem('deck-pwa-install-dismissed')).toBe('true')

    first.unmount()
    renderPrompt()
    dispatchInstallPrompt()
    expect(screen.queryByText(/instala deck/i)).not.toBeInTheDocument()
  })

  it('no interrumpe una partida activa', () => {
    useGameStore.getState().setGame({
      gameId: 'game-1',
      currentInning: 1,
      isTopInning: true,
      homeScore: 0,
      awayScore: 0,
      balls: 0,
      strikes: 0,
      outs: 0,
      runners: { b1: null, b2: null, b3: null },
      userRole: 'HOME',
    })
    renderPrompt()
    dispatchInstallPrompt()

    expect(screen.queryByText(/instala deck/i)).not.toBeInTheDocument()
  })
})
