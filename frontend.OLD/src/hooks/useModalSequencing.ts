import { useEffect, useRef } from 'react';

/**
 * Hook para manejar timing y secuenciación de modales
 * Controla: GameIntro, GameOver, InningTransition, Modal congelamiento
 */
export const useModalSequencing = (
  gameState: any,
  lastResult: any,
  inningCompleted: any,
  isAwaitingResult: boolean,
  setShowGameIntro: (v: boolean) => void,
  setShowGameOverModal: (v: boolean) => void,
  setInningTransition: (v: any) => void,
  setIsAwaitingResult: (v: boolean) => void,
  EVENT_SEQUENCES: any,
  EVENT_DURATIONS: any,
) => {
  const lastProcessedInningCompletedRef = useRef<number | null>(null);

  // Unfreeze cuando lastResult desaparece (overlay cierra)
  useEffect(() => {
    if (!lastResult && isAwaitingResult) {
      setIsAwaitingResult(false);
    }
  }, [lastResult, isAwaitingResult, setIsAwaitingResult]);

  // Detecta cuando la entrada termina y muestra modal de transición
  useEffect(() => {
    if (!inningCompleted || !gameState) return;

    // Evitar procesar el mismo inningCompleted dos veces
    if (lastProcessedInningCompletedRef.current === inningCompleted.ts) {
      return;
    }
    lastProcessedInningCompletedRef.current = inningCompleted.ts;

    // Si el juego ya terminó, NO mostrar modal de transición de entrada
    if (gameState?.isGameOver) {
      return;
    }

    const overlayDuration = EVENT_DURATIONS[lastResult?.event?.toUpperCase() ?? ''] ?? 1000 + 2500;

    const timer = setTimeout(() => {
      setInningTransition({
        visible: true,
        completedInning: inningCompleted.inning,
        completedHalf: inningCompleted.half,
        nextInning: inningCompleted.inning + (inningCompleted.half === 'BOT' ? 1 : 0),
        nextHalf: inningCompleted.half === 'TOP' ? 'BOT' : 'TOP',
      });
    }, overlayDuration);

    return () => clearTimeout(timer);
  }, [inningCompleted?.ts, gameState, lastResult, EVENT_DURATIONS, setInningTransition]);

  // Mostrar GameOverModal después del overlay final
  useEffect(() => {
    if (!gameState?.isGameOver) return;

    const eventKey = lastResult?.event?.toUpperCase() ?? '';
    const overlayDuration = EVENT_DURATIONS[eventKey] ?? 1000 + 2500;

    const timer = setTimeout(() => {
      setShowGameOverModal(true);
    }, overlayDuration);

    return () => clearTimeout(timer);
  }, [gameState?.isGameOver, lastResult, EVENT_DURATIONS, setShowGameOverModal]);

  // Cerrar inningTransition después de 3s
  useEffect(() => {
    const timer = setTimeout(() => {
      setInningTransition(null);
    }, 3000);

    return () => clearTimeout(timer);
  }, [setInningTransition]);
};
