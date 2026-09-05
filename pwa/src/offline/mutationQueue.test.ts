import { beforeEach, describe, expect, it, vi } from 'vitest'
import { offlineDb } from './db'
import {
  discardMutation,
  drainMutationQueue,
  enqueueMutation,
  retryDelay,
  retryFailedMutation,
} from './mutationQueue'

beforeEach(async () => {
  await offlineDb.offlineMutations.clear()
})

describe('offline mutation queue', () => {
  it('reemplaza una mutación pendiente con el último estado deseado', async () => {
    const first = await enqueueMutation({
      userId: 'user-1',
      operation: 'lineup.save',
      dedupeKey: 'lineup:user-1',
      payload: { slots: { P: 'card-1' } },
    })
    const latest = await enqueueMutation({
      userId: 'user-1',
      operation: 'lineup.save',
      dedupeKey: 'lineup:user-1',
      payload: { slots: { P: 'card-2' } },
    })

    expect(latest.id).toBe(first.id)
    expect(await offlineDb.offlineMutations.count()).toBe(1)
    expect(latest.payload).toEqual({ slots: { P: 'card-2' } })
  })

  it('elimina las operaciones sincronizadas y las ejecuta una sola vez', async () => {
    await enqueueMutation({
      userId: 'user-1',
      operation: 'lineup.save',
      dedupeKey: 'lineup:user-1',
      payload: { slots: {} },
    })
    const execute = vi.fn().mockResolvedValue(undefined)

    expect(await drainMutationQueue(execute, Date.now() + 1)).toEqual({
      succeeded: 1,
      retried: 0,
      failed: 0,
    })
    expect(execute).toHaveBeenCalledTimes(1)
    expect(await offlineDb.offlineMutations.count()).toBe(0)
  })

  it('aplica backoff y conserva el error tras agotar los reintentos', async () => {
    const queued = await enqueueMutation({
      userId: 'user-1',
      operation: 'lineup.save',
      dedupeKey: 'lineup:user-1',
      payload: {},
      maxAttempts: 2,
    })
    const execute = vi.fn().mockRejectedValue(new Error('Servidor no disponible'))
    const now = queued.createdAt + 1

    expect(await drainMutationQueue(execute, now)).toMatchObject({ retried: 1 })
    let stored = await offlineDb.offlineMutations.get(queued.id)
    expect(stored).toMatchObject({ attempts: 1, status: 'pending' })
    expect(stored?.nextAttemptAt).toBe(now + retryDelay(1))

    expect(await drainMutationQueue(execute, stored!.nextAttemptAt)).toMatchObject({ failed: 1 })
    stored = await offlineDb.offlineMutations.get(queued.id)
    expect(stored).toMatchObject({
      attempts: 2,
      status: 'failed',
      lastError: 'Servidor no disponible',
    })

    await retryFailedMutation(queued.id)
    expect(await offlineDb.offlineMutations.get(queued.id)).toMatchObject({
      attempts: 0,
      status: 'pending',
    })

    await discardMutation(queued.id)
    expect(await offlineDb.offlineMutations.get(queued.id)).toBeUndefined()
  })

  it('procesa operaciones distintas secuencialmente en orden de creación', async () => {
    const first = await enqueueMutation({
      userId: 'user-1',
      operation: 'first',
      dedupeKey: 'first:user-1',
      payload: {},
    })
    const second = await enqueueMutation({
      userId: 'user-1',
      operation: 'second',
      dedupeKey: 'second:user-1',
      payload: {},
    })
    await offlineDb.offlineMutations.update(first.id, { createdAt: 10 })
    await offlineDb.offlineMutations.update(second.id, { createdAt: 20 })
    const processed: string[] = []

    await drainMutationQueue(async (mutation) => {
      processed.push(mutation.operation)
    }, Date.now() + 1)

    expect(processed).toEqual(['first', 'second'])
  })
})
