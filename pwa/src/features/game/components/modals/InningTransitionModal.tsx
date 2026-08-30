import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

interface InningTransitionModalProps {
  completedInning: number
  completedHalf: 'TOP' | 'BOT'
  nextInning: number
  nextHalf: 'TOP' | 'BOT'
  homeScore: number
  awayScore: number
  userRole?: 'HOME' | 'AWAY'
}

export function InningTransitionModal({
  completedInning,
  completedHalf,
  nextInning,
  nextHalf,
  homeScore,
  awayScore,
  userRole = 'HOME',
}: InningTransitionModalProps) {
  const { t } = useTranslation()
  const userScore = userRole === 'HOME' ? homeScore : awayScore
  const cpuScore = userRole === 'HOME' ? awayScore : homeScore
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 1.67, 100))
    }, 16)

    return () => clearInterval(interval)
  }, [])

  const halfLabel = completedHalf === 'TOP' ? t('game.entry_top') : t('game.entry_bottom')
  const nextHalfLabel = nextHalf === 'TOP' ? t('game.entry_top') : t('game.entry_bottom')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md">
      <motion.div
        className="w-full max-w-md border-2 border-koshien-gold bg-[#0A0D0F] p-8 shadow-[0_0_50px_rgba(197,160,89,0.4)]"
        initial={{ opacity: 0, scale: 0.8, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.8, y: -20 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      >
        <div className="mb-6 text-center font-vintage">
          <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-koshien-gold">
            {t('game.entry_kicker')}
          </span>
          <h2 className="font-sports text-3xl uppercase tracking-wider text-koshien-chalk">
            3 OUTS
          </h2>
        </div>

        <motion.div
          className="mb-4 border border-koshien-border bg-koshien-dark p-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.3 }}
        >
          <p className="mb-2 text-center text-xs text-gray-400">{t('game.entry_completed')}</p>
          <p className="font-sports text-center text-2xl text-koshien-gold">
            {completedInning}ª {halfLabel}
          </p>
        </motion.div>

        <motion.div
          className="mb-4 flex items-center justify-around border border-koshien-border bg-koshien-dark p-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.3 }}
        >
          <div className="flex flex-col items-center">
            <span className="mb-1 text-xs text-gray-400">
              {userRole === 'HOME' ? t('game.home') : t('game.visitor')}
            </span>
            <span className="font-sports text-2xl text-koshien-gold">{userScore}</span>
          </div>
          <span className="font-sports text-xl text-gray-600">-</span>
          <div className="flex flex-col items-center">
            <span className="mb-1 text-xs text-gray-400">
              {userRole === 'HOME' ? t('game.visitor') : t('game.home')}
            </span>
            <span className="font-sports text-2xl text-koshien-chalk">{cpuScore}</span>
          </div>
        </motion.div>

        <motion.div
          className="mb-6 border border-[#4D7A5C] bg-koshien-green p-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.3 }}
        >
          <p className="mb-2 text-center text-xs text-[#7FBE9F]">{t('game.entry_next')}</p>
          <p className="font-sports text-center text-xl uppercase text-[#7FBE9F]">
            {nextInning}ª {nextHalfLabel}
          </p>
        </motion.div>

        <div className="h-2 overflow-hidden rounded-sm border border-koshien-border bg-[#0A0D0F]">
          <motion.div
            className="h-full bg-gradient-to-r from-koshien-gold to-[#7FBE9F]"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.05, ease: 'linear' }}
          />
        </div>
      </motion.div>
    </div>
  )
}