import { offlineDb, type StoredOfflineMutation } from './db'

export const DEFAULT_MAX_ATTEMPTS = 5
export const BASE_RETRY_DELAY_MS = 1_000
export const MAX_RETRY_DELAY_MS = 60_000

export interface EnqueueMutationInput {
  userId: string
  operation: string
  dedupeKey: string
  payload: unknown
  maxAttempts?: number
}

export type MutationExecutor = (mutation: StoredOfflineMutation) => Promise<void>

export interface DrainResult {
  succeeded: number
  retried: number
  failed: number
}

export class PermanentMutationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PermanentMutationError'
  }
}

export function retryDelay(attempts: number): number {
  return Math.min(BASE_RETRY_DELAY_MS * 2 ** Math.max(0, attempts - 1), MAX_RETRY_DELAY_MS)
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Error desconocido al sincronizar'
}

export async function enqueueMutation(input: EnqueueMutationInput): Promise<StoredOfflineMutation> {
  const now = Date.now()
  return offlineDb.transaction('rw', offlineDb.offlineMutations, async () => {
    const existing = await offlineDb.offlineMutations
      .where('dedupeKey')
      .equals(input.dedupeKey)
      .and((item) => item.userId === input.userId && item.status !== 'failed')
      .first()

    const mutation: StoredOfflineMutation = {
      id: existing?.id ?? crypto.randomUUID(),
      userId: input.userId,
      operation: input.operation,
      dedupeKey: input.dedupeKey,
      payload: input.payload,
      createdAt: existing?.createdAt ?? now,
      updatedAt: now,
      nextAttemptAt: now,
      attempts: 0,
      maxAttempts: input.maxAttempts ?? DEFAULT_MAX_ATTEMPTS,
      status: 'pending',
    }

    await offlineDb.offlineMutations.put(mutation)
    return mutation
  })
}

export async function drainMutationQueue(
  execute: MutationExecutor,
  now = Date.now(),
  userId?: string,
): Promise<DrainResult> {
  const result: DrainResult = { succeeded: 0, retried: 0, failed: 0 }
  const queued = await offlineDb.offlineMutations
    .where('status')
    .anyOf('pending', 'processing')
    .and((item) => item.nextAttemptAt <= now && (!userId || item.userId === userId))
    .sortBy('createdAt')

  for (const mutation of queued) {
    await offlineDb.offlineMutations.update(mutation.id, {
      status: 'processing',
      updatedAt: now,
    })

    try {
      await execute(mutation)
      await offlineDb.offlineMutations.delete(mutation.id)
      result.succeeded += 1
    } catch (error) {
      const attempts = mutation.attempts + 1
      const permanentlyFailed =
        error instanceof PermanentMutationError || attempts >= mutation.maxAttempts
      await offlineDb.offlineMutations.update(mutation.id, {
        attempts,
        status: permanentlyFailed ? 'failed' : 'pending',
        nextAttemptAt: permanentlyFailed ? now : now + retryDelay(attempts),
        updatedAt: now,
        lastError: errorMessage(error),
      })
      if (permanentlyFailed) result.failed += 1
      else result.retried += 1
    }
  }

  return result
}

export async function retryFailedMutation(id: string): Promise<void> {
  await offlineDb.offlineMutations.update(id, {
    status: 'pending',
    attempts: 0,
    nextAttemptAt: Date.now(),
    updatedAt: Date.now(),
    lastError: undefined,
  })
}

export async function discardMutation(id: string): Promise<void> {
  await offlineDb.offlineMutations.delete(id)
}
