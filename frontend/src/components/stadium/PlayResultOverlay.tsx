import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { soundFx } from '../../utils/audioManager';

interface PlayResultOverlayProps {
  resultText: string | null;
  resultEvent?: string | null;
  resultTs?: number | null;   // timestamp del hook — garantiza que el effect dispare siempre
  delayMs?: number;
}

// ---------------------------------------------------------------------------
// Configuración visual por tipo de evento
// ---------------------------------------------------------------------------
interface EventTheme {
  label: string;          // Etiqueta grande encima del texto descriptivo
  emoji: string;          // Emoji / icono decorativo
  bgGradient: string;     // Clases Tailwind para el fondo del panel
  borderColor: string;    // Color del borde (CSS)
  labelColor: string;     // Color del label grande (CSS)
  glowColor: string;      // rgba para el box-shadow exterior
  screenFlash: string;    // Clase Tailwind para el flash de pantalla
  scale: number;          // Escala máxima de la animación de entrada
  duration: number;       // Duración visible en ms (antes de ocultar)
}

const EVENT_THEMES: Record<string, EventTheme> = {
  HOME_RUN: {
    label: '¡HOME RUN!',
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
    label: '¡TRIPLE!',
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
    label: 'DOBLE',
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
    label: 'HIT SENCILLO',
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
    label: '¡PONCHE!',
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
    label: 'OUT ELEVADO',
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
    label: 'OUT ROLETAZO',
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
    label: 'BASE POR BOLAS',
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
    label: 'STRIKE',
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
    label: 'STRIKE CANTADO',
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
    label: 'BOLA',
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
    label: 'FOUL',
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
    label: '¡ROBO DE BASE!',
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
    label: 'FIN DEL JUEGO',
    emoji: '🏆',
    bgGradient: 'bg-gradient-to-b from-[#1A1200] to-[#0A0D0F]',
    borderColor: '#F59E0B',
    labelColor: '#FCD34D',
    glowColor: 'rgba(245, 158, 11, 0.9)',
    screenFlash: 'bg-yellow-400/20',
    scale: 1.12,
    duration: 3500,
  },
};

const DEFAULT_THEME: EventTheme = {
  label: 'JUGADA',
  emoji: '⚾',
  bgGradient: 'bg-gradient-to-b from-[#111] to-[#0A0D0F]',
  borderColor: '#C5A059',
  labelColor: '#F7F5F0',
  glowColor: 'rgba(197, 160, 89, 0.5)',
  screenFlash: 'bg-white/5',
  scale: 1.05,
  duration: 2500,
};

// ---------------------------------------------------------------------------
// Mapeo de eventos a métodos de audio
// ---------------------------------------------------------------------------
function playEventSound(eventKey: string): void {
  try {
    switch (eventKey) {
      case 'HOME_RUN':        soundFx.playHomeRun();  break;
      case 'HIT_3B':          soundFx.playHit3B();    break;
      case 'HIT_2B':          soundFx.playHit2B();    break;
      case 'HIT_1B':          soundFx.playHit1B();    break;
      case 'STRIKEOUT':       soundFx.playStrikeout(); break;
      case 'OUT_FLY':
      case 'OUT_GROUND':      soundFx.playOut();      break;
      case 'WALK':            soundFx.playWalk();     break;
      case 'STRIKE_SWINGING':
      case 'STRIKE_LOOKING':  soundFx.playStrike();   break;
      case 'BALL':            soundFx.playBall();     break;
      case 'FOUL':            soundFx.playFoul();     break;
      case 'STEAL':           soundFx.playHit1B();    break; // aplauso similar a sencillo
      default: break;
    }
  } catch {
    // Ignorar errores de audio (contexto suspendido, etc.)
  }
}
const Particles: React.FC<{ color: string; count: number }> = ({ color, count }) => (
  <>
    {Array.from({ length: count }).map((_, i) => (
      <motion.div
        key={i}
        className="absolute w-1.5 h-1.5 rounded-full pointer-events-none"
        style={{ backgroundColor: color, top: '50%', left: '50%' }}
        initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
        animate={{
          x: (Math.cos((i / count) * Math.PI * 2) * (80 + Math.random() * 80)),
          y: (Math.sin((i / count) * Math.PI * 2) * (80 + Math.random() * 80)),
          opacity: 0,
          scale: 0,
        }}
        transition={{ duration: 0.8 + Math.random() * 0.4, ease: 'easeOut', delay: 0.05 }}
      />
    ))}
  </>
);

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------
export const PlayResultOverlay: React.FC<PlayResultOverlayProps> = ({
  resultText,
  resultEvent,
  resultTs,
  delayMs = 0,
}) => {
  const [visible, setVisible] = useState(false);
  const [currentTheme, setCurrentTheme] = useState<EventTheme>(DEFAULT_THEME);
  const [currentText, setCurrentText] = useState<string>('');

  const pendingRef = useRef<{ text: string; theme: EventTheme } | null>(null);
  const [triggerCount, setTriggerCount] = useState(0);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Capturar tema y texto en cuanto llega el evento.
  // Depende de resultTs (timestamp único por jugada) — así dispara siempre,
  // incluso cuando dos jugadas consecutivas producen el mismo texto (ej. dos fouls).
  useEffect(() => {
    if (!resultText || !resultTs) return;
    const eventKey = resultEvent?.toUpperCase() ?? '';
    const theme = EVENT_THEMES[eventKey] ?? DEFAULT_THEME;
    pendingRef.current = { text: resultText, theme };
    setTriggerCount(c => c + 1);
  }, [resultTs]); // eslint-disable-line react-hooks/exhaustive-deps

  // Mostrar con delay, respetar la duración del tema
  useEffect(() => {
    if (triggerCount === 0 || !pendingRef.current) return;

    const { text, theme } = pendingRef.current;

    const showTimer = setTimeout(() => {
      // Limpiar timer previo si el usuario juega rápido
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);

      setCurrentTheme(theme);
      setCurrentText(text);
      setVisible(true);

      // Disparar el sonido del público en el mismo instante que aparece el overlay
      playEventSound(resultEvent?.toUpperCase() ?? '');

      hideTimerRef.current = setTimeout(() => {
        setVisible(false);
      }, theme.duration);
    }, delayMs);

    return () => clearTimeout(showTimer);
  }, [triggerCount, delayMs]);

  const isEpic = ['HOME_RUN', 'HIT_3B', 'STRIKEOUT', 'STEAL', 'GAME_OVER'].includes(
    resultEvent?.toUpperCase() ?? ''
  );

  return (
    <AnimatePresence>
      {visible && (
        <>
          {/* Flash de pantalla */}
          <motion.div
            className={`absolute inset-0 z-30 pointer-events-none ${currentTheme.screenFlash}`}
            initial={{ opacity: 1 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          />

          {/* Fondo oscuro */}
          <motion.div
            className="absolute inset-0 z-40 flex items-center justify-center pointer-events-none"
            style={{ background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.4) 100%)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Panel central */}
            <motion.div
              className={`relative flex flex-col items-center justify-center px-12 py-8 ${currentTheme.bgGradient} overflow-hidden`}
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
              {/* Líneas decorativas de esquina */}
              <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 pointer-events-none" style={{ borderColor: currentTheme.borderColor }} />
              <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 pointer-events-none" style={{ borderColor: currentTheme.borderColor }} />
              <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 pointer-events-none" style={{ borderColor: currentTheme.borderColor }} />
              <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 pointer-events-none" style={{ borderColor: currentTheme.borderColor }} />

              {/* Barra superior animada */}
              <motion.div
                className="absolute top-0 left-0 h-[3px] w-full"
                style={{ background: `linear-gradient(90deg, transparent, ${currentTheme.borderColor}, transparent)` }}
                animate={{ x: ['-100%', '100%'] }}
                transition={{ duration: 1.2, ease: 'easeInOut' }}
              />

              {/* Emoji */}
              <motion.div
                className="text-6xl mb-2 leading-none"
                initial={{ scale: 0, rotate: -20 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: 'spring', stiffness: 500, damping: 18, delay: 0.1 }}
              >
                {currentTheme.emoji}
              </motion.div>

              {/* Label del evento — texto grande de impacto */}
              <motion.h2
                className="font-sports tracking-[0.2em] uppercase text-center leading-none mb-3"
                style={{
                  color: currentTheme.labelColor,
                  fontSize: isEpic ? 'clamp(2.5rem, 6vw, 4.5rem)' : 'clamp(2rem, 5vw, 3.5rem)',
                  textShadow: `0 0 30px ${currentTheme.glowColor}, 0 0 60px ${currentTheme.glowColor.replace('0.', '0.4')}`,
                }}
                initial={{ scaleX: 3, opacity: 0 }}
                animate={{ scaleX: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
              >
                {currentTheme.label}
              </motion.h2>

              {/* Descripción del backend */}
              <motion.p
                className="font-mono text-sm text-center uppercase tracking-wider leading-snug max-w-md"
                style={{ color: '#E6DFD3', opacity: 0.85 }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 0.85, y: 0 }}
                transition={{ delay: 0.3, duration: 0.3 }}
              >
                {currentText}
              </motion.p>

              {/* Partículas solo en eventos épicos */}
              {isEpic && (
                <Particles
                  color={currentTheme.borderColor}
                  count={isEpic ? 16 : 8}
                />
              )}

              {/* Barra de progreso de duración */}
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
  );
};
