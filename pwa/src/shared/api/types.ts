export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: string
  username: string
}

export interface RegisterRequest {
  username: string
  password: string
}

export interface RegisterResponse {
  status: string
  user_id: string
  username: string
  has_completed_onboarding: boolean
}

export interface AuthUser {
  userId: string
  username: string
  hasCompletedOnboarding: boolean
}

export interface UserWallet {
  stamps: number
  gems: number
}

export interface UserProfileResponse {
  user_id: string
  username: string
  created_at: string
  wallet: UserWallet
  has_completed_onboarding: boolean
}

export interface Franchise {
  id: string
  name: string
  city: string
  color: string
  secondary_color: string
  badge: string
  desc: string
  ovr: number
  batOvr: number
  pitOvr: number
}

export interface CreateTeamRequest {
  name: string
  short_name: string
  city?: string
  stadium_name?: string
  primary_color?: string
  secondary_color?: string
  logo_id?: string
  base_franchise: string
}

export interface UserTeam {
  id: number
  user_id: string
  name: string
  short_name: string
  city: string
  stadium_name: string
  primary_color: string
  secondary_color: string
  logo_id: string
  base_franchise: string
}

export interface PitchAttribute {
  pitch_type: string
  velocity: number
  control: number
  movement: number
}

export type CardRarity = 'COMMON' | 'BRONZE' | 'SILVER' | 'GOLD' | 'DIAMOND'

export interface PlayerCard {
  id: string
  team_id: string | null
  name: string
  number: string
  position: string
  overall: number
  rarity: CardRarity
  is_two_way: boolean
  power: number
  contact: number
  velocity: number
  control: number
  movement: number
  repertoire: PitchAttribute[] | null
}

export interface StarterPackResponse {
  message: string
  user_id: string
  cards_claimed: number
  cards: PlayerCard[]
}
