import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getLineup, saveLineup } from '@/features/team/api'
import { ApiError } from '@/shared/api/errors'
import { offlineDb } from './db'
import { enqueueMutation } from './mutationQueue'
import {
  SAVE_LINEUP_OPERATION,
  saveLineupOfflineFirst,
  syncOfflineMutations,
} from './sync'

vi.mock('@/features/team/api', () => ({ getLineup: vi.fn(), saveLineup: vi.fn() }))

const payload = { name: 'Principal', slots: { P: 'card-1' } }
const baseSlots = { P: 'card-old' }
const queuedPayload = { desired: payload, baseSlots }

function setOnline(value: boolean) {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value })
}

beforeEach(async () => {
  vi.clearAllMocks()
  setOnline(true)
  await offlineDb.offlineMutations.clear()
})

describe('offline lineup synchronization', () => {
  it('guarda el lineup en cola y devuelve estado optimista cuando no hay conexión', async () => {
    setOnline(false)

    const result = await saveLineupOfflineFirst('user-1', payload, baseSlots)

    expect(result).toMatchObject({ queued: true, lineup: { user_id: 'user-1', ...payload } })
    expect(saveLineup).not.toHaveBeenCalled()
    expect(await offlineDb.offlineMutations.count()).toBe(1)
  })

  it('guarda directamente cuando el servidor está disponible', async () => {
    const response = { user_id: 'user-1', ...payload }
    vi.mocked(saveLineup).mockResolvedValue(response)

    await expect(saveLineupOfflineFirst('user-1', payload, baseSlots)).resolves.toEqual({
      queued: false,
      lineup: response,
    })
    expect(await offlineDb.offlineMutations.count()).toBe(0)
  })

  it('sincroniza únicamente las operaciones del usuario activo', async () => {
    await enqueueMutation({
      userId: 'user-1',
      operation: SAVE_LINEUP_OPERATION,
      dedupeKey: 'lineup:user-1',
      payload: queuedPayload,
    })
    await enqueueMutation({
      userId: 'user-2',
      operation: SAVE_LINEUP_OPERATION,
      dedupeKey: 'lineup:user-2',
      payload: queuedPayload,
    })
    vi.mocked(getLineup).mockResolvedValue({
      user_id: 'user-1',
      name: 'Principal',
      slots: baseSlots,
    })
    vi.mocked(saveLineup).mockResolvedValue({ user_id: 'user-1', ...payload })

    expect(await syncOfflineMutations('user-1')).toMatchObject({ succeeded: 1 })
    expect(await offlineDb.offlineMutations.toArray()).toHaveLength(1)
    expect((await offlineDb.offlineMutations.toArray())[0]?.userId).toBe('user-2')
  })

  it('marca como definitivo un rechazo no reintentable del servidor', async () => {
    const queued = await enqueueMutation({
      userId: 'user-1',
      operation: SAVE_LINEUP_OPERATION,
      dedupeKey: 'lineup:user-1',
      payload: queuedPayload,
    })
    vi.mocked(getLineup).mockResolvedValue({
      user_id: 'user-1',
      name: 'Principal',
      slots: baseSlots,
    })
    vi.mocked(saveLineup).mockRejectedValue(new ApiError(422, 'Lineup inválido'))

    expect(await syncOfflineMutations('user-1')).toMatchObject({ failed: 1 })
    expect(await offlineDb.offlineMutations.get(queued.id)).toMatchObject({
      status: 'failed',
      lastError: 'Lineup inválido',
    })
  })

  it('no repite el PUT cuando el servidor ya contiene el estado deseado', async () => {
    await enqueueMutation({
      userId: 'user-1',
      operation: SAVE_LINEUP_OPERATION,
      dedupeKey: 'lineup:user-1',
      payload: queuedPayload,
    })
    vi.mocked(getLineup).mockResolvedValue({ user_id: 'user-1', ...payload })

    expect(await syncOfflineMutations('user-1')).toMatchObject({ succeeded: 1 })
    expect(saveLineup).not.toHaveBeenCalled()
  })

  it('detecta un cambio remoto y evita sobrescribirlo silenciosamente', async () => {
    const queued = await enqueueMutation({
      userId: 'user-1',
      operation: SAVE_LINEUP_OPERATION,
      dedupeKey: 'lineup:user-1',
      payload: queuedPayload,
    })
    vi.mocked(getLineup).mockResolvedValue({
      user_id: 'user-1',
      name: 'Principal',
      slots: { P: 'remote-new-card' },
    })

    expect(await syncOfflineMutations('user-1')).toMatchObject({ failed: 1 })
    expect(saveLineup).not.toHaveBeenCalled()
    expect(await offlineDb.offlineMutations.get(queued.id)).toMatchObject({
      status: 'failed',
      lastError: expect.stringContaining('cambió en el servidor'),
    })
  })
})
