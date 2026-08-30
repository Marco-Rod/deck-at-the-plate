import { http } from '@/shared/api/client'
import type { StarterPackResponse } from '@/shared/api/types'

export function claimStarterPack(teamId: string): Promise<StarterPackResponse> {
  return http
    .post<StarterPackResponse>('/api/v1/shop/starter-pack', undefined, {
      params: { team_id: teamId },
    })
    .then((response) => response.data)
}
