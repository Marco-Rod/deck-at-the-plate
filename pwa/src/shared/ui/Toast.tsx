import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, XCircle } from 'lucide-react'

export type ToastTone = 'success' | 'error'

interface Props {
  open: boolean
  tone?: ToastTone
  message: string
  onClose: () => void
}

export function Toast({ open, tone = 'success', message, onClose }: Props) {
  const Icon = tone === 'success' ? CheckCircle2 : XCircle
  const toneClass =
    tone === 'success' ? 'border-koshien-gold/60 text-koshien-gold' : 'border-red-500/60 text-red-400'

  useEffect(() => {
    if (!open) return
    const timeout = setTimeout(onClose, 3000)
    return () => clearTimeout(timeout)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          role="status"
          aria-live="polite"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          transition={{ type: 'spring', damping: 24, stiffness: 300 }}
          className="fixed bottom-[max(1.5rem,env(safe-area-inset-bottom))] left-1/2 z-[60] flex w-full max-w-sm -translate-x-1/2 items-center gap-3 rounded-xl border bg-koshien-dark px-4 py-3 shadow-scoreboard"
        >
          <Icon className={`h-5 w-5 shrink-0 ${toneClass}`} aria-hidden />
          <p className="font-vintage text-xs uppercase tracking-widest text-koshien-cream">
            {message}
          </p>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}
