import { getLineup, saveLineup } from '@/features/team/api'
import type { LineupResponse } from '@/shared/api/types'
import { ApiError } from '@/shared/api/errors'
import { offlineDb, type StoredOfflineMutation } from './db'
import {
  drainMutationQueue,
  enqueueMutation,
  PermanentMutationError,
  type DrainResult,
} from './mutationQueue'

export const SAVE_LINEUP_OPERATION = 'lineup.save'
export const OFFLINE_QUEUE_CHANGED_EVENT = 'deck-offline-queue-changed'

export interface SaveLineupPayload {
  name?: string
  slots: Record<string, string>
}

interface QueuedLineupPayload {
  desired: SaveLineupPayload
  baseSlots: Record<string, string>
}

export interface OfflineSaveResult {
  lineup: LineupResponse
  queued: boolean
}

function optimisticLineup(userId: string, payload: SaveLineupPayload): LineupResponse {
  return {
    user_id: userId,
    name: payload.name ?? 'Lineup Principal',
    slots: payload.slots,
  }
}

function shouldQueue(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 0 || error.status >= 500)
}

function sameSlots(left: Record<string, string>, right: Record<string, string>): boolean {
  const leftEntries = Object.entries(left).sort(([a], [b]) => a.localeCompare(b))
  const rightEntries = Object.entries(right).sort(([a], [b]) => a.localeCompare(b))
  return JSON.stringify(leftEntries) === JSON.stringify(rightEntries)
}

async function queueLineup(
  userId: string,
  payload: SaveLineupPayload,
  baseSlots: Record<string, string>,
): Promise<OfflineSaveResult> {
  const dedupeKey = `lineup:${userId}`
  const existing = await offlineDb.offlineMutations
    .where('dedupeKey')
    .equals(dedupeKey)
    .and((item) => item.userId === userId && item.status !== 'failed')
    .first()
  const originalBase = (existing?.payload as QueuedLineupPayload | undefined)?.baseSlots ?? baseSlots

  await enqueueMutation({
    userId,
    operation: SAVE_LINEUP_OPERATION,
    dedupeKey,
    payload: { desired: payload, baseSlots: originalBase } satisfies QueuedLineupPayload,
  })
  window.dispatchEvent(new Event(OFFLINE_QUEUE_CHANGED_EVENT))
  return { lineup: optimisticLineup(userId, payload), queued: true }
}

export async function saveLineupOfflineFirst(
  userId: string,
  payload: SaveLineupPayload,
  baseSlots: Record<string, string>,
): Promise<OfflineSaveResult> {
  if (!navigator.onLine) return queueLineup(userId, payload, baseSlots)

  try {
    return { lineup: await saveLineup(payload), queued: false }
  } catch (error) {
    if (shouldQueue(error)) return queueLineup(userId, payload, baseSlots)
    throw error
  }
}

async function executeMutation(mutation: StoredOfflineMutation): Promise<void> {
  if (mutation.operation !== SAVE_LINEUP_OPERATION) {
    throw new PermanentMutationError(`Operación offline no soportada: ${mutation.operation}`)
  }

  const queued = mutation.payload as QueuedLineupPayload
  try {
    const serverLineup = await getLineup()
    if (sameSlots(serverLineup.slots, queued.desired.slots)) return
    if (!sameSlots(serverLineup.slots, queued.baseSlots)) {
      throw new PermanentMutationError(
        'El lineup cambió en el servidor mientras estabas sin conexión. Revisa los cambios antes de reintentarlo.',
      )
    }
    await saveLineup(queued.desired)
  } catch (error) {
    if (error instanceof PermanentMutationError) throw error
    if (!shouldQueue(error)) {
      throw new PermanentMutationError(
        error instanceof Error ? error.message : 'La operación fue rechazada por el servidor',
      )
    }
    throw error
  }
}

export function syncOfflineMutations(userId: string): Promise<DrainResult> {
  return drainMutationQueue(executeMutation, Date.now(), userId).then((result) => {
    window.dispatchEvent(new Event(OFFLINE_QUEUE_CHANGED_EVENT))
    return result
  })
}
