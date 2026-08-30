import { useCallback, useEffect, useRef, useState } from 'react'

export type EventSequenceStep = { name: string; delay: number }

export interface EventSequence {
  displayDuration: number
  steps: EventSequenceStep[]
}

export const EVENT_SEQUENCES: Record<string, EventSequence> = {
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
}

const MAX_QUEUE_SIZE = 50

let idCounter = 0

export interface QueuedGameEvent {
  id: string
  type: string
  payload: unknown
  createdAt: number
  order: number
  status: 'pending' | 'processing' | 'completed'
}

export type StepCallback = (payload: unknown, stepName: string) => void | Promise<void>

export interface UseEventSequencerReturn {
  queue: QueuedGameEvent[]
  currentEvent: QueuedGameEvent | null
  isProcessing: boolean
  enqueueEvent: (type: string, payload: unknown) => void
  onStep: (stepName: string, callback: StepCallback) => void
}

function generateId(): string {
  idCounter += 1
  return `${Date.now()}-${idCounter}-${Math.random().toString(36).slice(2, 9)}`
}

function getMaxStepDelay(steps: EventSequenceStep[]): number {
  return Math.max(...steps.map((step) => step.delay), 0)
}

export function useEventSequencer(): UseEventSequencerReturn {
  const queueRef = useRef<QueuedGameEvent[]>([])
  const stepCallbacksRef = useRef<Map<string, StepCallback>>(new Map())
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  const processingRef = useRef(false)
  const startNextRef = useRef<() => void>(() => {})

  const [queue, setQueue] = useState<QueuedGameEvent[]>([])
  const [currentEvent, setCurrentEvent] = useState<QueuedGameEvent | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const clearEventTimers = (eventId: string) => {
    Array.from(timersRef.current.keys()).forEach((key) => {
      if (key.startsWith(eventId)) {
        const timer = timersRef.current.get(key)
        if (timer) clearTimeout(timer)
        timersRef.current.delete(key)
      }
    })
  }

  const startNext = useCallback(() => {
    if (processingRef.current) return
    const next = queueRef.current[0]
    if (!next) return

    processingRef.current = true
    setIsProcessing(true)
    setCurrentEvent(next)

    const sequence = EVENT_SEQUENCES[next.type]
    if (!sequence) {
      console.error(`[EVENT SEQUENCER] Sequence not defined for: ${next.type}`)
      queueRef.current = queueRef.current.slice(1)
      setQueue([...queueRef.current])
      processingRef.current = false
      setIsProcessing(false)
      setCurrentEvent(null)
      setTimeout(() => startNextRef.current(), 0)
      return
    }

    sequence.steps.forEach((step) => {
      const timer = setTimeout(() => {
        const callback = stepCallbacksRef.current.get(step.name)
        if (callback) {
          try {
            void callback(next.payload, step.name)
          } catch (err) {
            console.error(`[EVENT SEQUENCER] Error en step ${step.name}:`, err)
          }
        }
      }, step.delay)
      timersRef.current.set(`${next.id}-${step.name}`, timer)
    })

    const completionTimer = setTimeout(() => {
      clearEventTimers(next.id)
      queueRef.current = queueRef.current.slice(1)
      setQueue([...queueRef.current])
      setCurrentEvent(null)
      processingRef.current = false
      setIsProcessing(false)
      setTimeout(() => startNextRef.current(), 0)
    }, getMaxStepDelay(sequence.steps) + 500)

    timersRef.current.set(`${next.id}-complete`, completionTimer)
  }, [])

  useEffect(() => {
    startNextRef.current = startNext
  }, [startNext])

  const enqueueEvent = useCallback(
    (type: string, payload: unknown) => {
      const base = queueRef.current.length >= MAX_QUEUE_SIZE ? queueRef.current.slice(1) : [...queueRef.current]
      const newEvent: QueuedGameEvent = {
        id: generateId(),
        type,
        payload,
        createdAt: Date.now(),
        order: base.length,
        status: 'pending',
      }
      queueRef.current = [...base, newEvent]
      setQueue([...queueRef.current])
      startNext()
    },
    [startNext],
  )

  const onStep = useCallback((stepName: string, callback: StepCallback) => {
    stepCallbacksRef.current.set(stepName, callback)
  }, [])

  return {
    queue,
    currentEvent,
    isProcessing: isProcessing || queue.length > 0,
    enqueueEvent,
    onStep,
  }
}