import { http } from '@/shared/api/client'
import type {
  AvailablePitchersResponse,
  BoxScoreResponse,
  ChangePitcherResponse,
  GameSessionResponse,
  PlayResultResponse,
  SwingType,
} from '@/shared/api/types'

export function getGameState(gameId: string): Promise<GameSessionResponse> {
  return http.get<GameSessionResponse>(`/api/v1/games/${gameId}`).then((response) => response.data)
}

export function pitch(
  gameId: string,
  payload: { pitch_type: string; zone: number },
): Promise<PlayResultResponse> {
  return http
    .post<PlayResultResponse>(`/api/v1/games/${gameId}/pitch`, payload)
    .then((response) => response.data)
}

export function swing(
  gameId: string,
  payload: { swing_type: SwingType; guessed_zone: number | null; guessed_pitch: string | null },
): Promise<PlayResultResponse> {
  return http
    .post<PlayResultResponse>(`/api/v1/games/${gameId}/swing`, payload)
    .then((response) => response.data)
}

export function playTactic(
  gameId: string,
  payload: { player_role: 'PITCHER' | 'BATTER'; tactic_id: string },
): Promise<PlayResultResponse> {
  return http
    .post<PlayResultResponse>(`/api/v1/games/${gameId}/play-tactic`, payload)
    .then((response) => response.data)
}

export function steal(gameId: string, payload: { target_base: string }): Promise<PlayResultResponse> {
  return http
    .post<PlayResultResponse>(`/api/v1/games/${gameId}/steal`, payload)
    .then((response) => response.data)
}

export function changePitcher(
  gameId: string,
  payload: { new_pitcher_id: string; player_role: string },
): Promise<ChangePitcherResponse> {
  return http
    .post<ChangePitcherResponse>(`/api/v1/games/${gameId}/change-pitcher`, payload)
    .then((response) => response.data)
}

export function getAvailablePitchers(gameId: string): Promise<AvailablePitchersResponse> {
  return http
    .get<AvailablePitchersResponse>(`/api/v1/games/${gameId}/available-pitchers`)
    .then((response) => response.data)
}

export function getRivalAvailablePitchers(gameId: string): Promise<AvailablePitchersResponse> {
  return http
    .get<AvailablePitchersResponse>(`/api/v1/games/${gameId}/rival-available-pitchers`)
    .then((response) => response.data)
}

export function acknowledgePitcherChange(gameId: string): Promise<unknown> {
  return http
    .post<unknown>(`/api/v1/games/${gameId}/acknowledge-pitcher-change`)
    .then((response) => response.data)
}

export function getBoxScore(gameId: string): Promise<BoxScoreResponse> {
  return http
    .get<BoxScoreResponse>(`/api/v1/games/${gameId}/box-score`)
    .then((response) => response.data)
}