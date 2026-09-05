import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

interface SubmitPlayButtonProps {
  label: string
  disabled?: boolean
  onSubmit: () => void
}

export function SubmitPlayButton({ label, disabled = false, onSubmit }: SubmitPlayButtonProps) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center">
      <motion.button
        type="button"
        onClick={onSubmit}
        disabled={disabled}
        className={`relative flex items-center gap-3 overflow-hidden rounded-sm border-2 border-orange-500 bg-[#1A100A] px-8 py-3.5 font-sports text-3xl tracking-widest text-koshien-chalk shadow-2xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
          disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'
        }`}
        animate={{
          boxShadow: [
            '0 0 15px rgba(239, 68, 68, 0.6), inset 0 0 10px rgba(249, 115, 22, 0.4)',
            '0 0 35px rgba(249, 115, 22, 0.9), inset 0 0 20px rgba(234, 179, 8, 0.7)',
            '0 0 15px rgba(239, 68, 68, 0.6), inset 0 0 10px rgba(249, 115, 22, 0.4)',
          ],
          borderColor: ['#ef4444', '#f97316', '#eab308', '#ef4444'],
          scale: [1, 1.03, 1],
        }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
        whileHover={{
          scale: 1.07,
          backgroundColor: '#381404',
          borderColor: '#f97316',
          rotate: [0, -1, 1, -1, 1, 0],
          transition: {
            rotate: { repeat: Infinity, duration: 0.12 },
            scale: { duration: 0.2 },
          },
        }}
        whileTap={{ scale: 0.95 }}
      >
        <div className="pointer-events-none absolute inset-0 flex items-end justify-center overflow-hidden">
          {Array.from({ length: 4 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute h-8 w-4 rounded-full bg-gradient-to-t from-red-600 via-orange-500 to-yellow-400 opacity-60 blur-[1px]"
              initial={{ y: 15, x: (i - 2) * 20, scale: 0.4, opacity: 0 }}
              animate={{
                y: [-5, -35, -50],
                x: [(i - 2) * 20, (i - 2) * 25 + (i % 2 === 0 ? 8 : -8)],
                scale: [0.4, 1, 0.1],
                opacity: [0, 0.7, 0],
              }}
              transition={{ duration: 1 + i * 0.2, repeat: Infinity, ease: 'easeOut', delay: i * 0.25 }}
            />
          ))}
        </div>

        <motion.div
          className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-orange-500/30 to-transparent"
          animate={{ x: ['-100%', '100%'] }}
          transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}
        />

        <span className="relative z-10 flex items-center gap-3 text-orange-200 drop-shadow-[0_0_8px_rgba(249,115,22,0.8)]">
          {label}
        </span>
      </motion.button>

      <span className="mt-1 font-vintage text-[9px] font-bold uppercase tracking-wider text-orange-400">
        {t('game.confirm_play')}
      </span>
    </div>
  )
}
