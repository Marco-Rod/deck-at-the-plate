import { http } from '@/shared/api/client'
import type { CreateGameRequest, GameSessionResponse } from '@/shared/api/types'

export function createGame(payload: CreateGameRequest): Promise<GameSessionResponse> {
  return http
    .post<GameSessionResponse>('/api/v1/games/create', payload)
    .then((response) => response.data)
}
