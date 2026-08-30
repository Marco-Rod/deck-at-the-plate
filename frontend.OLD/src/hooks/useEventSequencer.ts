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
 * Movido FUERA del componente para evitar que EVENT_SEQUENCES sea una nueva referencia cada render
 */
const EVENT_SEQUENCES_STABLE = {
  HOME_RUN: {
    displayDuration: 3500,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-score', delay: 3600 },
      { name: 'update-batter-stats', delay: 3700 },
      { name: 'update-runners', delay: 3800 },
      { name: 'load-next-batter', delay: 4000 },
      { name: 'close-modal', delay: 4100 },
    ],
  },
  STRIKEOUT: {
    displayDuration: 2500,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2600 },
      { name: 'update-pitcher-stats', delay: 2700 },
      { name: 'check-inning-end', delay: 2800 },
      { name: 'close-modal', delay: 2900 },
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
      { name: 'close-modal', delay: 3300 },
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
      { name: 'close-modal', delay: 3500 },
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
      { name: 'close-modal', delay: 3500 },
    ],
  },
  OUT_FLY: {
    displayDuration: 2400,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2500 },
      { name: 'update-pitcher-stats', delay: 2600 },
      { name: 'check-inning-end', delay: 2700 },
      { name: 'close-modal', delay: 2800 },
    ],
  },
  OUT_GROUND: {
    displayDuration: 2400,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2500 },
      { name: 'update-pitcher-stats', delay: 2600 },
      { name: 'check-inning-end', delay: 2700 },
      { name: 'close-modal', delay: 2800 },
    ],
  },
  BALL: {
    displayDuration: 1800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-balls', delay: 1900 },
      { name: 'close-modal', delay: 2000 },
    ],
  },
  STRIKE: {
    displayDuration: 1800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-strikes', delay: 1900 },
      { name: 'close-modal', delay: 2000 },
    ],
  },
  STRIKE_LOOKING: {
    displayDuration: 1800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-strikes', delay: 1900 },
      { name: 'close-modal', delay: 2000 },
    ],
  },
  STRIKE_SWINGING: {
    displayDuration: 1800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-strikes', delay: 1900 },
      { name: 'close-modal', delay: 2000 },
    ],
  },
  PITCHER_CHANGED: {
    displayDuration: 2000,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-pitcher-card', delay: 2100 },
      { name: 'reset-pitch-selector', delay: 2150 },
      { name: 'close-modal', delay: 2250 },
    ],
  },
  FOUL: {
    displayDuration: 1800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-strikes', delay: 1900 },
      { name: 'close-modal', delay: 2000 },
    ],
  },
  WALK: {
    displayDuration: 2400,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-runners', delay: 1600 },
      { name: 'load-next-batter', delay: 1800 },
      { name: 'close-modal', delay: 1900 },
    ],
  },
  DOUBLE_PLAY: {
    displayDuration: 2600,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2700 },
      { name: 'update-runners', delay: 2800 },
      { name: 'check-inning-end', delay: 2900 },
      { name: 'close-modal', delay: 3000 },
    ],
  },
  GAME_OVER: {
    displayDuration: 3000,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'close-modal', delay: 3100 },
    ],
  },
};

// Export como EVENT_SEQUENCES para mantener compatibilidad con código existente
export const EVENT_SEQUENCES = EVENT_SEQUENCES_STABLE;

/**
 * Durations for each event type (for modal overlay timing)
 */
export const EVENT_DURATIONS: Record<keyof typeof EVENT_SEQUENCES_STABLE, number> = {
  HOME_RUN: 3500,
  STRIKEOUT: 2500,
  HIT_1B: 2800,
  HIT_2B: 3000,
  HIT_3B: 3000,
  OUT_FLY: 2400,
  OUT_GROUND: 2400,
  BALL: 1800,
  STRIKE: 1800,
  STRIKE_LOOKING: 1800,
  STRIKE_SWINGING: 1800,
  PITCHER_CHANGED: 2000,
  FOUL: 1800,
  WALK: 2400,
  DOUBLE_PLAY: 2600,
  GAME_OVER: 3000,
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
    console.log(`📌 [REGISTER STEP] Registering callback for step: ${stepName}`);
    stepCallbacksRef.current.set(stepName, callback);
    console.log(`   ✅ Step "${stepName}" now has callback. Total steps registered: ${stepCallbacksRef.current.size}`);
  }, []);

  /**
   * Procesar el evento actual
   */
  // ⚠️ CRITICAL BUGFIX: El problema es que setQueue() y setCurrentEvent() happen en el same setTimeout
  // Esto causa que el useEffect no se re-ejecute a tiempo para procesar el siguiente evento
  // SOLUCIÓN: Usar isProcessing state como trigger para re-ejecutar
  useEffect(() => {
    // Si la queue tiene eventos y no estamos procesando, iniciar el siguiente
    if (queue.length > 0 && !isProcessing) {
      const event = queue[0];
      setIsProcessing(true);
      processingRef.current = true;
      const eventStartTime = Date.now();
      
      setCurrentEvent(event);
      console.log(`⚙️  [EVENT SEQUENCER] Processing event: ${event.type} (id: ${event.id})`);
      console.log(`   🕐 Event sequence starting at T=${eventStartTime}`);
      console.log(`   📋 Available callbacks: ${Array.from(stepCallbacksRef.current.keys()).join(', ')}`);

      const sequence = EVENT_SEQUENCES_STABLE[event.type];
      if (!sequence) {
        console.error(`❌ [EVENT SEQUENCER] Sequence not defined for: ${event.type}`);
        setQueue(prev => prev.slice(1));
        processingRef.current = false;
        setIsProcessing(false);
        return;
      }

      // Ejecutar cada step en su momento exacto
      sequence.steps.forEach(step => {
        const timer = setTimeout(() => {
          console.log(`   ⏱️  [STEP TIMEOUT] ${step.name} timeout fired at T=${Date.now()}`);
          const callback = stepCallbacksRef.current.get(step.name);
          console.log(`   🔍 Looking for callback "${step.name}" - Found: ${callback ? 'YES ✅' : 'NO ❌'}`);
          
          if (callback) {
            try {
              const stepExecTime = Date.now();
              console.log(`  📍 [STEP] ${step.name} (delay: ${step.delay}ms) - executing callback at T=${stepExecTime} (+${stepExecTime - eventStartTime}ms from start)`);
              const result = callback(event.payload, step.name);
              if (result instanceof Promise) {
                result.catch(err => {
                  console.error(`  ❌ [STEP] Error in ${step.name}:`, err);
                });
              }
              const stepEndTime = Date.now();
              console.log(`      ✅ ${step.name} completed in ${stepEndTime - stepExecTime}ms`);
            } catch (err) {
              console.error(`  ❌ [STEP] Error in ${step.name}:`, err);
            }
          } else {
            console.warn(`  ⚠️  [STEP] No callback registered for ${step.name}`);
            console.log(`      Current callbacks in ref: ${Array.from(stepCallbacksRef.current.keys()).join(', ')}`);
          }
        }, step.delay);

        timersRef.current.set(`${event.id}-${step.name}`, timer);
      });

      // Calculate completion time based on maximum step delay
      const maxStepDelay = getMaxStepDelay(sequence.steps);
      const eventCompletionTime = maxStepDelay + 500;

      // Cuando el evento se completa, removerlo de la queue y procesar el siguiente
      const completeTimer = setTimeout(() => {
        console.log(`✅ [EVENT SEQUENCER] Event completed: ${event.type}`);
        console.log(`   📊 Queue before removal: ${queue.length}, After will be: ${queue.length - 1}`);
        console.log(`   🔓 Setting isProcessing to FALSE to allow next event`);
        
        // Limpiar todos los timers de este evento ANTES de actualizar la queue
        Array.from(timersRef.current.keys()).forEach(key => {
          if (key.startsWith(event.id)) {
            const timer = timersRef.current.get(key);
            if (timer) clearTimeout(timer);
            timersRef.current.delete(key);
          }
        });
        
        setQueue(prev => {
          console.log(`   🔄 setQueue called: removing first event, new length: ${prev.length - 1}`);
          return prev.slice(1);
        });
        setCurrentEvent(null);
        processingRef.current = false;
        console.log(`   ✋ processingRef.current set to false`);
        setIsProcessing(false);
        console.log(`   ✅ setIsProcessing(false) executed`);
      }, eventCompletionTime);

      timersRef.current.set(`${event.id}-complete`, completeTimer);
      console.log(`   ⏰ Complete timer scheduled for ${eventCompletionTime}ms`);

      return () => {
        // NO hacer cleanup aquí para evitar cancelar timers en progreso
        // Los timers ya se limpian en el completion handler
      };
    }
  }, [queue.length]); // ← BUGFIX: Solo queue.length, no isProcessing. Esto evita cancelar el setTimeout cuando isProcessing cambia

  return {
    queue,
    currentEvent,
    isProcessing: queue.length > 0,
    enqueueEvent,
    onStep,
  };
};
