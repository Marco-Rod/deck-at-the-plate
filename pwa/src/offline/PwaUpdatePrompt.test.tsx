import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { RegisterSWOptions } from 'vite-plugin-pwa/types'
import '@/shared/lib/i18n'
import { useGameStore } from '@/features/game/store'
import { PwaUpdatePrompt } from './PwaUpdatePrompt'

const pwaMocks = vi.hoisted(() => ({ register: vi.fn(), update: vi.fn() }))

vi.mock('virtual:pwa-register', () => ({ registerSW: pwaMocks.register }))

function registeredOptions(): RegisterSWOptions {
  return pwaMocks.register.mock.calls[0]?.[0] as RegisterSWOptions
}

beforeEach(() => {
  pwaMocks.update.mockResolvedValue(undefined)
  pwaMocks.register.mockReturnValue(pwaMocks.update)
  useGameStore.getState().resetGame()
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('PwaUpdatePrompt', () => {
  it('informa una versión nueva y permite aplicarla de forma controlada', async () => {
    render(<PwaUpdatePrompt />)
    act(() => registeredOptions().onNeedRefresh?.())

    expect(screen.getByText(/nueva versión disponible/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^actualizar$/i }))
    await waitFor(() => expect(pwaMocks.update).toHaveBeenCalledWith(true))
  })

  it('impide recargar durante una partida activa', () => {
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
    render(<PwaUpdatePrompt />)
    act(() => registeredOptions().onNeedRefresh?.())

    expect(screen.getByText(/partida activa antes de actualizar/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^actualizar$/i })).toBeDisabled()
  })

  it('revalida el registro cuando la pestaña vuelve a estar visible', () => {
    const registration = { update: vi.fn().mockResolvedValue(undefined) }
    render(<PwaUpdatePrompt />)
    act(() => registeredOptions().onRegisteredSW?.('/sw.js', registration as unknown as ServiceWorkerRegistration))
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })

    act(() => document.dispatchEvent(new Event('visibilitychange')))

    expect(registration.update).toHaveBeenCalledTimes(1)
  })
})
