import { useRef, useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useDialogFocus } from './useDialogFocus'

function Fixture() {
  const [open, setOpen] = useState(false)
  const dialogRef = useRef<HTMLDivElement>(null)
  useDialogFocus({ active: open, containerRef: dialogRef, onEscape: () => setOpen(false) })
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>Abrir</button>
      {open ? (
        <div ref={dialogRef} role="dialog" tabIndex={-1}>
          <button type="button">Primero</button>
          <button type="button" onClick={() => setOpen(false)}>Último</button>
        </div>
      ) : null}
    </>
  )
}

describe('useDialogFocus', () => {
  it('mueve, contiene y devuelve el foco', async () => {
    render(<Fixture />)
    const trigger = screen.getByRole('button', { name: 'Abrir' })
    trigger.focus()
    fireEvent.click(trigger)

    const first = await screen.findByRole('button', { name: 'Primero' })
    await new Promise((resolve) => requestAnimationFrame(resolve))
    expect(first).toHaveFocus()

    const last = screen.getByRole('button', { name: 'Último' })
    last.focus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(first).toHaveFocus()

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })
})
