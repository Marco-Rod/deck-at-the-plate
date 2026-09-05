import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'

const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  '[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

interface DialogFocusOptions {
  active: boolean
  containerRef: RefObject<HTMLElement | null>
  onEscape?: () => void
}

export function useDialogFocus({ active, containerRef, onEscape }: DialogFocusOptions) {
  const onEscapeRef = useRef(onEscape)
  useEffect(() => {
    onEscapeRef.current = onEscape
  }, [onEscape])

  useEffect(() => {
    if (!active) return

    const previouslyFocused = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const container = containerRef.current
    if (!container) return

    const focusInitialControl = () => {
      const firstControl = container.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)
      ;(firstControl ?? container).focus()
    }
    const focusFrame = window.requestAnimationFrame(focusInitialControl)

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && onEscapeRef.current) {
        event.preventDefault()
        onEscapeRef.current()
        return
      }
      if (event.key !== 'Tab') return

      const controls = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
      if (controls.length === 0) {
        event.preventDefault()
        container.focus()
        return
      }

      const first = controls[0]!
      const last = controls[controls.length - 1]!
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      window.cancelAnimationFrame(focusFrame)
      document.removeEventListener('keydown', handleKeyDown)
      previouslyFocused?.focus()
    }
  }, [active, containerRef])
}
