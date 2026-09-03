import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

interface PlayResultOverlayProps {
  resultText: string | null
  resultEvent?: string | null
  resultTs?: number | null
  delayMs?: number
}

interface EventTheme {
  labelKey: string
  emoji: string
  bgGradient: string
  borderColor: string
  labelColor: string
  glowColor: string
  screenFlash: string
  scale: number
  duration: number
}

const EVENT_THEMES: Record<string, EventTheme> = {
  HOME_RUN: {
    labelKey: 'game.event_home_run',
    emoji: '💥',
    bgGradient: 'bg-gradient-to-b from-[#3A1800] to-[#0A0D0F]',
    borderColor: '#F59E0B',
    labelColor: '#FCD34D',
    glowColor: 'rgba(245, 158, 11, 0.9)',
    screenFlash: 'bg-yellow-400/20',
    scale: 1.15,
    duration: 3500,
  },
  HIT_3B: {
    labelKey: 'game.event_hit_3b',
    emoji: '🚀',
    bgGradient: 'bg-gradient-to-b from-[#0A2A0A] to-[#0A0D0F]',
    borderColor: '#22C55E',
    labelColor: '#86EFAC',
    glowColor: 'rgba(34, 197, 94, 0.8)',
    screenFlash: 'bg-green-500/15',
    scale: 1.1,
    duration: 3000,
  },
  HIT_2B: {
    labelKey: 'game.event_hit_2b',
    emoji: '⚡',
    bgGradient: 'bg-gradient-to-b from-[#0A2A0A] to-[#0A0D0F]',
    borderColor: '#4ADE80',
    labelColor: '#86EFAC',
    glowColor: 'rgba(74, 222, 128, 0.7)',
    screenFlash: 'bg-green-500/10',
    scale: 1.08,
    duration: 2800,
  },
  HIT_1B: {
    labelKey: 'game.event_hit_1b',
    emoji: '🎯',
    bgGradient: 'bg-gradient-to-b from-[#0A2A0A] to-[#0A0D0F]',
    borderColor: '#86EFAC',
    labelColor: '#86EFAC',
    glowColor: 'rgba(134, 239, 172, 0.6)',
    screenFlash: 'bg-green-400/10',
    scale: 1.05,
    duration: 2500,
  },
  STRIKEOUT: {
    labelKey: 'game.event_strikeout',
    emoji: '🔥',
    bgGradient: 'bg-gradient-to-b from-[#2A0A0A] to-[#0A0D0F]',
    borderColor: '#EF4444',
    labelColor: '#FCA5A5',
    glowColor: 'rgba(239, 68, 68, 0.8)',
    screenFlash: 'bg-red-500/15',
    scale: 1.1,
    duration: 2800,
  },
  OUT_FLY: {
    labelKey: 'game.event_out_fly',
    emoji: '🫳',
    bgGradient: 'bg-gradient-to-b from-[#1A0A0A] to-[#0A0D0F]',
    borderColor: '#F87171',
    labelColor: '#FCA5A5',
    glowColor: 'rgba(248, 113, 113, 0.6)',
    screenFlash: 'bg-red-400/10',
    scale: 1.05,
    duration: 2500,
  },
  OUT_GROUND: {
    labelKey: 'game.event_out_ground',
    emoji: '⬇️',
    bgGradient: 'bg-gradient-to-b from-[#1A0A0A] to-[#0A0D0F]',
    borderColor: '#F87171',
    labelColor: '#FCA5A5',
    glowColor: 'rgba(248, 113, 113, 0.6)',
    screenFlash: 'bg-red-400/10',
    scale: 1.05,
    duration: 2500,
  },
  WALK: {
    labelKey: 'game.event_walk',
    emoji: '🚶',
    bgGradient: 'bg-gradient-to-b from-[#0A1A2A] to-[#0A0D0F]',
    borderColor: '#60A5FA',
    labelColor: '#93C5FD',
    glowColor: 'rgba(96, 165, 250, 0.7)',
    screenFlash: 'bg-blue-400/10',
    scale: 1.05,
    duration: 2500,
  },
  STRIKE_SWINGING: {
    labelKey: 'game.event_strike_swinging',
    emoji: '💨',
    bgGradient: 'bg-gradient-to-b from-[#1A1200] to-[#0A0D0F]',
    borderColor: '#C5A059',
    labelColor: '#FCD34D',
    glowColor: 'rgba(197, 160, 89, 0.5)',
    screenFlash: 'bg-yellow-500/8',
    scale: 1.03,
    duration: 2000,
  },
  STRIKE_LOOKING: {
    labelKey: 'game.event_strike_looking',
    emoji: '🎙️',
    bgGradient: 'bg-gradient-to-b from-[#1A1200] to-[#0A0D0F]',
    borderColor: '#C5A059',
    labelColor: '#FCD34D',
    glowColor: 'rgba(197, 160, 89, 0.5)',
    screenFlash: 'bg-yellow-500/8',
    scale: 1.03,
    duration: 2000,
  },
  BALL: {
    labelKey: 'game.event_ball',
    emoji: '⚾',
    bgGradient: 'bg-gradient-to-b from-[#0A0F1A] to-[#0A0D0F]',
    borderColor: '#64748B',
    labelColor: '#94A3B8',
    glowColor: 'rgba(100, 116, 139, 0.4)',
    screenFlash: 'bg-slate-400/5',
    scale: 1.02,
    duration: 1800,
  },
  FOUL: {
    labelKey: 'game.event_foul',
    emoji: '↩️',
    bgGradient: 'bg-gradient-to-b from-[#1A1A0A] to-[#0A0D0F]',
    borderColor: '#A3A300',
    labelColor: '#D4D400',
    glowColor: 'rgba(163, 163, 0, 0.5)',
    screenFlash: 'bg-yellow-600/8',
    scale: 1.02,
    duration: 1800,
  },
  STEAL: {
    labelKey: 'game.event_steal',
    emoji: '💨',
    bgGradient: 'bg-gradient-to-b from-[#0A1A2A] to-[#0A0D0F]',
    borderColor: '#38BDF8',
    labelColor: '#7DD3FC',
    glowColor: 'rgba(56, 189, 248, 0.7)',
    screenFlash: 'bg-sky-400/10',
    scale: 1.08,
    duration: 2500,
  },
  GAME_OVER: {
    labelKey: 'game.event_game_over',
    emoji: '🏆',
    bgGradient: 'bg-gradient-to-b from-[#1A1200] to-[#0A0D0F]',
    borderColor: '#F59E0B',
    labelColor: '#FCD34D',
    glowColor: 'rgba(245, 158, 11, 0.9)',
    screenFlash: 'bg-yellow-400/20',
    scale: 1.12,
    duration: 3500,
  },
}

const DEFAULT_THEME: EventTheme = {
  labelKey: 'game.event_default',
  emoji: '⚾',
  bgGradient: 'bg-gradient-to-b from-[#111111] to-[#0A0D0F]',
  borderColor: '#C5A059',
  labelColor: '#F7F5F0',
  glowColor: 'rgba(197, 160, 89, 0.5)',
  screenFlash: 'bg-white/5',
  scale: 1.05,
  duration: 2500,
}

const pseudoRandom = (n: number) => ((n * 1103515245 + 12345) % 10000) / 10000

function Particles({ color, count }: { color: string; count: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className="pointer-events-none absolute h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: color, top: '50%', left: '50%' }}
          initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
          animate={{
            x: Math.cos((i / count) * Math.PI * 2) * (80 + pseudoRandom(i + 1) * 80),
            y: Math.sin((i / count) * Math.PI * 2) * (80 + pseudoRandom(i + 37) * 80),
            opacity: 0,
            scale: 0,
          }}
          transition={{
            duration: 0.8 + pseudoRandom(i * 3 + 5) * 0.4,
            ease: 'easeOut',
            delay: 0.05,
          }}
        />
      ))}
    </>
  )
}

export function PlayResultOverlay({
  resultText,
  resultEvent,
  resultTs,
  delayMs = 0,
}: PlayResultOverlayProps) {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(false)
  const [currentTheme, setCurrentTheme] = useState<EventTheme>(DEFAULT_THEME)
  const [currentText, setCurrentText] = useState('')

  useEffect(() => {
    if (!resultText || !resultTs) {
      setVisible(false)
      return
    }
    const eventKey = resultEvent?.toUpperCase() ?? ''
    const theme = EVENT_THEMES[eventKey] ?? DEFAULT_THEME

    const showTimer = setTimeout(() => {
      setCurrentTheme(theme)
      setCurrentText(resultText)
      setVisible(true)
    }, delayMs)

    const hideTimer = setTimeout(() => setVisible(false), delayMs + theme.duration)

    return () => {
      clearTimeout(showTimer)
      clearTimeout(hideTimer)
    }
  }, [resultTs, delayMs, resultText, resultEvent])

  const eventKey = resultEvent?.toUpperCase() ?? ''
  const isEpic = ['HOME_RUN', 'HIT_3B', 'STRIKEOUT', 'STEAL', 'GAME_OVER'].includes(eventKey)

  return (
    <AnimatePresence>
      {visible && (
        <>
          <motion.div
            className={`pointer-events-none absolute inset-0 z-30 ${currentTheme.screenFlash}`}
            initial={{ opacity: 1 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          />

          <motion.div
            className="pointer-events-none absolute inset-0 z-40 flex items-center justify-center"
            style={{
              background:
                'radial-gradient(ellipse at center, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.4) 100%)',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <motion.div
              className={`relative flex flex-col items-center justify-center overflow-hidden px-12 py-8 ${currentTheme.bgGradient}`}
              style={{
                border: `3px solid ${currentTheme.borderColor}`,
                boxShadow: `0 0 60px ${currentTheme.glowColor}, 0 0 120px ${currentTheme.glowColor.replace('0.', '0.3')}, inset 0 0 30px rgba(0,0,0,0.8)`,
                minWidth: '420px',
                maxWidth: '700px',
              }}
              initial={{ scale: 0.3, opacity: 0, y: 40 }}
              animate={{ scale: currentTheme.scale, opacity: 1, y: 0 }}
              exit={{ scale: 0.8, opacity: 0, y: -20 }}
              transition={{ type: 'spring', stiffness: 400, damping: 22, duration: 0.4 }}
            >
              <div
                className="pointer-events-none absolute top-0 left-0 h-8 w-8 border-t-2 border-l-2"
                style={{ borderColor: currentTheme.borderColor }}
              />
              <div
                className="pointer-events-none absolute top-0 right-0 h-8 w-8 border-t-2 border-r-2"
                style={{ borderColor: currentTheme.borderColor }}
              />
              <div
                className="pointer-events-none absolute bottom-0 left-0 h-8 w-8 border-b-2 border-l-2"
                style={{ borderColor: currentTheme.borderColor }}
              />
              <div
                className="pointer-events-none absolute right-0 bottom-0 h-8 w-8 border-r-2 border-b-2"
                style={{ borderColor: currentTheme.borderColor }}
              />

              <motion.div
                className="absolute top-0 left-0 h-[3px] w-full"
                style={{
                  background: `linear-gradient(90deg, transparent, ${currentTheme.borderColor}, transparent)`,
                }}
                animate={{ x: ['-100%', '100%'] }}
                transition={{ duration: 1.2, ease: 'easeInOut' }}
              />

              <motion.div
                className="mb-2 text-6xl leading-none"
                initial={{ scale: 0, rotate: -20 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: 'spring', stiffness: 500, damping: 18, delay: 0.1 }}
              >
                {currentTheme.emoji}
              </motion.div>

              <motion.h2
                className="mb-3 text-center font-sports uppercase leading-none tracking-[0.2em]"
                style={{
                  color: currentTheme.labelColor,
                  fontSize: isEpic ? 'clamp(2.5rem, 6vw, 4.5rem)' : 'clamp(2rem, 5vw, 3.5rem)',
                  textShadow: `0 0 30px ${currentTheme.glowColor}, 0 0 60px ${currentTheme.glowColor.replace('0.', '0.4')}`,
                }}
                initial={{ scaleX: 3, opacity: 0 }}
                animate={{ scaleX: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
              >
                {t(currentTheme.labelKey)}
              </motion.h2>

              <motion.p
                className="max-w-md font-vintage text-center text-sm uppercase leading-snug tracking-wider"
                style={{ color: '#E6DFD3', opacity: 0.85 }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 0.85, y: 0 }}
                transition={{ delay: 0.3, duration: 0.3 }}
              >
                {currentText}
              </motion.p>

              {isEpic && <Particles color={currentTheme.borderColor} count={16} />}

              <motion.div
                className="absolute bottom-0 left-0 h-[3px]"
                style={{ background: currentTheme.borderColor }}
                initial={{ width: '100%' }}
                animate={{ width: '0%' }}
                transition={{ duration: currentTheme.duration / 1000, ease: 'linear', delay: 0.2 }}
              />
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}