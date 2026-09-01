import { http } from '@/shared/api/client'
import type { PlayerCard } from '@/shared/api/types'

export function getCard(cardId: string): Promise<PlayerCard> {
  return http.get<PlayerCard>(`/api/v1/cards/${cardId}`).then((response) => response.data)
}
