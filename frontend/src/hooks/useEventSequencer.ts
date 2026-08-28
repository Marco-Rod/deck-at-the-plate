/**
 * useEventSequencer Hook
 * ======================
 * Manages ordered execution of game events with controlled state updates.
 * 
 * Problema que resuelve:
 * - Actualmente los eventos se actualizar sin orden, causando visual glitches
 * - El usuario ve cambios en la UI ANTES de ver el modal que los explica
 * - Esto rompe la narrativa del juego
 * 
 * Solución:
 * - Queue de eventos ordenados
 * - Cada evento define su secuencia de actualizaciones
 * - Cada actualización tiene un delay relativo
 * - Ejecución estricta: una cosa después de otra
 * 
 * Ejemplo:
 * HOME_RUN: 
 *   1. Mostrar modal (0ms - 3500ms)
 *   2. Actualizar score (3600ms)
 *   3. Actualizar stats del bateador (3700ms)
 *   4. Actualizar runners (3800ms)
 *   5. Cargar nuevo bateador (4000ms)
 */

import { useRef, useState, useEffect, useCallback } from 'react';

/**
 * Simple ID generator (no external dependencies)
 */
const generateId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Calculate the maximum delay from event sequence steps
 */
const getMaxStepDelay = (steps: Array<{ name: string; delay: number }>): number => {
  return Math.max(...steps.map(s => s.delay), 0);
};

/**
 * Define qué ocurre en cada tipo de evento y en qué orden
 */
export const EVENT_SEQUENCES = {
  HOME_RUN: {
    displayDuration: 3500,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-score', delay: 3600 },
      { name: 'update-batter-stats', delay: 3700 },
      { name: 'update-runners', delay: 3800 },
      { name: 'load-next-batter', delay: 4000 },
    ],
  },
  STRIKEOUT: {
    displayDuration: 2500,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2600 },
      { name: 'update-pitcher-stats', delay: 2700 },
      { name: 'check-inning-end', delay: 2800 },
    ],
  },
  HIT_1B: {
    displayDuration: 2800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-score', delay: 2900 },
      { name: 'update-batter-stats', delay: 3000 },
      { name: 'update-runners', delay: 3100 },
      { name: 'load-next-batter', delay: 3200 },
    ],
  },
  HIT_2B: {
    displayDuration: 3000,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-score', delay: 3100 },
      { name: 'update-batter-stats', delay: 3200 },
      { name: 'update-runners', delay: 3300 },
      { name: 'load-next-batter', delay: 3400 },
    ],
  },
  HIT_3B: {
    displayDuration: 3000,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-score', delay: 3100 },
      { name: 'update-batter-stats', delay: 3200 },
      { name: 'update-runners', delay: 3300 },
      { name: 'load-next-batter', delay: 3400 },
    ],
  },
  OUT_FLYBALL: {
    displayDuration: 2400,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2500 },
      { name: 'update-pitcher-stats', delay: 2600 },
      { name: 'check-inning-end', delay: 2700 },
    ],
  },
  OUT_GROUNDBALL: {
    displayDuration: 2400,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2500 },
      { name: 'update-pitcher-stats', delay: 2600 },
      { name: 'check-inning-end', delay: 2700 },
    ],
  },
  BALL: {
    displayDuration: 1800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-balls', delay: 1900 },
    ],
  },
  STRIKE: {
    displayDuration: 1800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-strikes', delay: 1900 },
    ],
  },
  PITCHER_CHANGED: {
    displayDuration: 2000,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-pitcher-card', delay: 2100 },
      { name: 'reset-pitch-selector', delay: 2150 },
    ],
  },
  FOUL: {
    displayDuration: 1800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-strikes', delay: 1900 },
    ],
  },
  WALK: {
    displayDuration: 2400,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-runners', delay: 1600 },
      { name: 'load-next-batter', delay: 1800 },
    ],
  },
  DOUBLE_PLAY: {
    displayDuration: 2600,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2700 },
      { name: 'update-runners', delay: 2800 },
      { name: 'check-inning-end', delay: 2900 },
    ],
  },
};

/**
 * Evento en la queue
 */
export interface QueuedGameEvent {
  id: string;
  type: keyof typeof EVENT_SEQUENCES;
  payload: any;
  createdAt: number;
  order: number;
  status: 'pending' | 'processing' | 'completed';
}

/**
 * Callback que se ejecuta en cada step
 */
export type StepCallback = (payload: any, stepName: string) => void | Promise<void>;

/**
 * Return type del hook
 */
export interface UseEventSequencerReturn {
  queue: QueuedGameEvent[];
  currentEvent: QueuedGameEvent | null;
  isProcessing: boolean;
  enqueueEvent: (type: keyof typeof EVENT_SEQUENCES, payload: any) => void;
  onStep: (stepName: string, callback: StepCallback) => void;
}

/**
 * Hook principal para gestionar la secuencia ordenada de eventos
 */
export const useEventSequencer = (): UseEventSequencerReturn => {
  const [queue, setQueue] = useState<QueuedGameEvent[]>([]);
  const [currentEvent, setCurrentEvent] = useState<QueuedGameEvent | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const processingRef = useRef(false);
  const stepCallbacksRef = useRef<Map<string, StepCallback>>(new Map());
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  /**
   * Agregar un evento a la queue
   */
  const enqueueEvent = useCallback((type: keyof typeof EVENT_SEQUENCES, payload: any) => {
    const MAX_QUEUE_SIZE = 50;
    
    setQueue(prev => {
      // Evitar que la queue crezca indefinidamente
      if (prev.length >= MAX_QUEUE_SIZE) {
        console.warn(`⚠️  [EVENT QUEUE] Queue full (${prev.length}), dropping oldest event`);
        prev = prev.slice(1);
      }

      const newEvent: QueuedGameEvent = {
        id: generateId(),
        type,
        payload,
        createdAt: Date.now(),
        order: prev.length,
        status: 'pending',
      };

      console.log(`📤 [EVENT QUEUE] Enqueued: ${type} (order: ${newEvent.order}, queue size: ${prev.length + 1})`);
      return [...prev, newEvent];
    });
  }, []);

  /**
   * Registrar un callback para un step específico
   */
  const onStep = useCallback((stepName: string, callback: StepCallback) => {
    stepCallbacksRef.current.set(stepName, callback);
  }, []);

  /**
   * Procesar el evento actual
   */
  useEffect(() => {
    if (queue.length === 0 || processingRef.current) return;

    processingRef.current = true;
    const event = queue[0];
    
    setCurrentEvent(event);
    console.log(`⚙️  [EVENT SEQUENCER] Processing event: ${event.type} (id: ${event.id})`);

    const sequence = EVENT_SEQUENCES[event.type];
    if (!sequence) {
      console.error(`❌ [EVENT SEQUENCER] Sequence not defined for: ${event.type}`);
      setQueue(prev => prev.slice(1));
      processingRef.current = false;
      return;
    }

    // Ejecutar cada step en su momento exacto
    sequence.steps.forEach(step => {
      const timer = setTimeout(() => {
        const callback = stepCallbacksRef.current.get(step.name);
        if (callback) {
          try {
            console.log(`  📍 [STEP] ${step.name} (delay: ${step.delay}ms) - executing callback`);
            // Execute callback without awaiting in setTimeout
            // If it's a promise, let it resolve independently
            const result = callback(event.payload, step.name);
            if (result instanceof Promise) {
              result.catch(err => {
                console.error(`  ❌ [STEP] Error in ${step.name}:`, err);
              });
            }
          } catch (err) {
            console.error(`  ❌ [STEP] Error in ${step.name}:`, err);
          }
        } else {
          console.warn(`  ⚠️  [STEP] No callback registered for ${step.name}`);
        }
      }, step.delay);

      timersRef.current.set(`${event.id}-${step.name}`, timer);
    });

    // Calculate completion time based on maximum step delay (Error #2 fix)
    const maxStepDelay = getMaxStepDelay(sequence.steps);
    const eventCompletionTime = maxStepDelay + 500; // 500ms buffer after last step

    // Cuando el evento se completa, removerlo de la queue y procesar el siguiente
    const completeTimer = setTimeout(() => {
      console.log(`✅ [EVENT SEQUENCER] Event completed: ${event.type}`);
      
      setQueue(prev => prev.slice(1));
      setCurrentEvent(null);
      processingRef.current = false;
      
      // Limpiar todos los timers de este evento específicamente (Error #5 fix)
      Array.from(timersRef.current.keys()).forEach(key => {
        if (key.startsWith(event.id)) {
          const timer = timersRef.current.get(key);
          if (timer) clearTimeout(timer);
          timersRef.current.delete(key);
        }
      });
    }, eventCompletionTime);

    timersRef.current.set(`${event.id}-complete`, completeTimer);

    return () => {
      // Cleanup: cancelar solo los timers de este evento específico
      Array.from(timersRef.current.keys()).forEach(key => {
        if (key.startsWith(event.id)) {
          const timer = timersRef.current.get(key);
          if (timer) clearTimeout(timer);
          timersRef.current.delete(key);
        }
      });
    };
  }, [queue]);

  return {
    queue,
    currentEvent,
    isProcessing: queue.length > 0,
    enqueueEvent,
    onStep,
  };
};
