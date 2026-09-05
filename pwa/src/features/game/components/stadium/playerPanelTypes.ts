import type { PitchAttribute } from '@/shared/api/types'

export interface PitcherSummary {
  id: string
  name: string
  number: string
  overall: number
  velocity: number
  control: number
  movement: number
  stamina: number
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
