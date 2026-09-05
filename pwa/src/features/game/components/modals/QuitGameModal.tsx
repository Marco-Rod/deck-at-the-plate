import { useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useDialogFocus } from '@/shared/ui/useDialogFocus'

interface QuitGameModalProps {
  isOpen: boolean
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
}

export function QuitGameModal({
  isOpen,
  onConfirm,
  onCancel,
  isLoading = false,
}: QuitGameModalProps) {
  const { t } = useTranslation()
  const dialogRef = useRef<HTMLDivElement>(null)
  useDialogFocus({
    active: isOpen,
    containerRef: dialogRef,
    onEscape: isLoading ? undefined : onCancel,
  })

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onCancel}
            className="fixed inset-0 z-50 bg-black/75"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              ref={dialogRef}
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="quit-game-title"
              aria-describedby="quit-game-description"
              tabIndex={-1}
              className="pointer-events-auto w-full max-w-md rounded-xl border-2 border-koshien-gold/50 bg-[#0F1419]/95 shadow-2xl backdrop-blur-md"
            >
              <div className="flex items-center justify-between border-b border-koshien-gold/30 px-6 py-4">
                <h2 id="quit-game-title" className="font-vintage text-xl font-bold tracking-wide text-koshien-cream">
                  {t('game.quit_title')}
                </h2>
              </div>

              <div className="px-6 py-6">
                <p id="quit-game-description" className="mb-4 text-sm leading-relaxed text-koshien-cream">
                  {t('game.quit_confirm')}
                </p>
                <p className="font-vintage text-xs text-[#A89968]">{t('game.quit_note')}</p>
              </div>

              <div className="flex justify-end gap-3 border-t border-koshien-gold/20 px-6 py-4">
                <button
                  type="button"
                  onClick={onCancel}
                  disabled={isLoading}
                  className="rounded-lg border border-koshien-gold/50 px-4 py-2 font-vintage text-sm font-bold text-koshien-gold transition-colors hover:bg-koshien-gold/10 disabled:opacity-50"
                >
                  {t('game.cancel')}
                </button>
                <motion.button
                  type="button"
                  onClick={onConfirm}
                  disabled={isLoading}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className=" rounded-lg bg-red-600 px-6 py-2 font-vintage text-sm font-bold text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-block animate-spin">⟳</span>
                      {t('game.quitting')}
                    </span>
                  ) : (
                    t('game.quit_finalize')
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
