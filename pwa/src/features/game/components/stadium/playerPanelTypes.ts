import type { FatigueBand, PitchAttribute } from '@/shared/api/types'

export interface PitcherSummary {
  id: string
  name: string
  number: string
  overall: number
  velocity: number
  control: number
  movement: number
  /** Progresión de barra (0-100). Con factor=banda derivada; sin factor, legacy `100 - fatigue_level`. */
  stamina: number
  /** Semántica vigente (001D-5): null = fallback legacy con fatigue_level. */
  fatigueBand: FatigueBand | null
  pitchCount: number
  rarity: string
  repertoire: PitchAttribute[] | null
}

export interface BatterSummary {
  id: string
  name: string
  number: string
  overall: number
  contact: number
  power: number
  speed: number
  rarity: string
}
