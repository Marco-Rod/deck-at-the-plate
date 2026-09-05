import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import '@/shared/lib/i18n'
import { useAuthStore } from '@/features/auth/store'
import { OfflineSyncStatus } from './OfflineSyncStatus'
import { OnlineRequiredHint } from './OnlineRequiredHint'
import { useOnlineStatus } from './useOnlineStatus'

function setOnline(value: boolean) {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value })
}

function StatusProbe() {
  const online = useOnlineStatus()
  return <output>{online ? 'online' : 'offline'}</output>
}

afterEach(() => {
  cleanup()
  setOnline(true)
})

describe('connectivity UI', () => {
  it('reacciona a los eventos online y offline', () => {
    setOnline(true)
    render(<StatusProbe />)
    expect(screen.getByText('online')).toBeInTheDocument()

    act(() => {
      setOnline(false)
      window.dispatchEvent(new Event('offline'))
    })
    expect(screen.getByText('offline')).toBeInTheDocument()

    act(() => {
      setOnline(true)
      window.dispatchEvent(new Event('online'))
    })
    expect(screen.getByText('online')).toBeInTheDocument()
  })

  it('explica textualmente por qué una acción no está disponible', () => {
    const { rerender } = render(<OnlineRequiredHint id="connection-help" visible />)
    expect(screen.getByRole('note')).toHaveAttribute('id', 'connection-help')
    expect(screen.getByText(/requiere conexión/i)).toBeInTheDocument()

    rerender(<OnlineRequiredHint id="connection-help" visible={false} />)
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

  it('anuncia tanto la desconexión como la recuperación de la conexión', () => {
    useAuthStore.setState({ token: null, user: null, profileLoaded: true })
    setOnline(false)
    render(<OfflineSyncStatus />)
    expect(screen.getByRole('alert')).toHaveTextContent(/sin conexión/i)
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive')

    act(() => {
      setOnline(true)
      window.dispatchEvent(new Event('online'))
    })
    expect(screen.getByRole('status')).toHaveTextContent(/conexión recuperada/i)
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite')
  })
})
