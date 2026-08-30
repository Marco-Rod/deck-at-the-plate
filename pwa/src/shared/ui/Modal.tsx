import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'

interface Props {
  open: boolean
  title?: string
  onClose: () => void
  children: ReactNode
}

export function Modal({ open, title, onClose, children }: Props) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          role="presentation"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-4"
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ type: 'spring', damping: 24, stiffness: 300 }}
            onClick={(event) => event.stopPropagation()}
            className="w-full max-w-md rounded-t-2xl border border-koshien-border bg-koshien-dark p-5 shadow-scoreboard sm:rounded-2xl"
          >
            <div className="mb-4 flex items-center justify-between gap-2">
              {title ? (
                <h2 className="font-sports text-xl font-bold uppercase tracking-wide text-koshien-chalk">
                  {title}
                </h2>
              ) : (
                <span />
              )}
              <button
                type="button"
                aria-label="Cerrar"
                onClick={onClose}
                className="rounded p-1 text-koshien-cream/70 transition-colors hover:text-koshien-gold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}
