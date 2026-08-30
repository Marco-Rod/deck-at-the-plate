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

export interface InventoryItem {
  inventory_id: string
  acquired_at: string
  card: PlayerCard
}

export interface UserInventoryResponse {
  user_id: string
  total_cards: number
  inventory: InventoryItem[]
}

export interface LineupResponse {
  user_id: string
  name: string
  slots: Record<string, string>
}

export type GameMode = 'PVE' | 'PVP'
export type Difficulty = 'EASY' | 'MEDIUM' | 'HARD'
export type PlayerPosition = 'HOME' | 'AWAY'

export interface CreateGameRequest {
  home_user_id: string
  away_user_id?: string
  game_mode?: GameMode
  difficulty?: Difficulty
  total_innings?: number
  player_position?: PlayerPosition
  home_pitcher_id?: string
  away_pitcher_id?: string
  home_lineup?: string[]
  away_lineup?: string[]
  home_tactics_deck?: string[]
  away_tactics_deck?: string[]
}

export interface GameSessionResponse {
  id: string
  home_user_id: string
  away_user_id: string
  current_inning: number
  is_top_inning: boolean
  outs: number
  balls: number
  strikes: number
  score_home: number
  score_away: number
  state_data: Record<string, unknown>
}

export interface ChangePitcherResponse {
  status: string
  message: string
  active_pitcher_id: string
  active_pitcher: PlayerGameData
}

export interface AvailablePitchersResponse {
  status: string
  count: number
  available_pitchers: PlayerGameData[]
}

export interface TacticalCard {
  id: string
  name: string
  cost: number
  desc: string
  type: string
  color: string
  icon: string
}

export interface TacticalCard {
  id: string
  label: string
  icon: string
  desc: string
}

export interface TeamStatsResponse {
  overall: number
  batting: number
  pitching: number
}

// ─── Gameplay / Stadium ───────────────────────────────────────────────

export type PlayerRole = 'PITCHER' | 'BATTER'
export type SwingType = 'NORMAL' | 'POWER' | 'TAKE' | 'BUNT'
export type GameConnectionMode = 'ws' | 'polling'

export interface PlayerStat {
  label: string
  val: number
}

export interface PlayerGameData {
  id: string
  name: string
  number: string
  overall: number
  position: string
  photo: string
  team?: string
  role: PlayerRole
  rarity?: string
  repertoire?: PitchAttribute[]
  stats: PlayerStat[]
  pitch_count?: number
  fatigue_level?: number
}

export interface GameRunners {
  b1: string | null
  b2: string | null
  b3: string | null
}

export interface BatterStats {
  at_bats: number
  hits: number
  doubles: number
  triples: number
  home_runs: number
  rbi: number
  runs: number
  strikeouts: number
  walks: number
}

export interface GameStateWS {
  gameId: string
  currentInning: number
  isTopInning: boolean
  homeScore: number
  awayScore: number
  balls: number
  strikes: number
  outs: number
  runners: GameRunners
  totalInnings?: number
  lastEvent?: string
  isGameOver?: boolean
  winnerMessage?: string
  activePitcherId?: string
  activeBatterId?: string
  rivalTeamName?: string
  userRole: 'HOME' | 'AWAY'
  state_data?: Record<string, unknown>
  pitcher_strikeouts?: Record<string, number>
  batter_stats?: Record<string, BatterStats>
  homeHits?: number
  awayHits?: number
  inning_runs?: Record<string, number>
  active_pitcher?: PlayerGameData
  active_batter?: PlayerGameData
  inning_completed?: boolean
}

export interface PlayResolvedPayload {
  type: 'PLAY_RESOLVED'
  event: string
  description: string
  outs: number
  balls: number
  strikes: number
  score_home: number
  score_away: number
  current_inning: number
  is_top_inning: boolean
  state_data: Record<string, unknown>
  inning_completed?: boolean
  pitcher_strikeouts?: Record<string, number>
  batter_stats?: Record<string, BatterStats>
  home_hits?: number
  away_hits?: number
  inning_runs?: Record<string, number>
  active_pitcher?: PlayerGameData
  active_batter?: PlayerGameData
}

export interface StealResolvedPayload {
  type: 'STEAL_RESOLVED'
  event: string
  description: string
  outs: number
  balls: number
  strikes: number
  score_home: number
  score_away: number
  current_inning: number
  is_top_inning: boolean
  state_data: Record<string, unknown>
  inning_completed?: boolean
  home_hits?: number
  away_hits?: number
}

export interface PitchCommittedPayload {
  type: 'PITCH_COMMITTED'
  message: string
  has_pitched: boolean
}

export interface InitGameStatePayload {
  type: 'INIT_GAME_STATE'
  game_id: string
  outs: number
  balls: number
  strikes: number
  score_home: number
  score_away: number
  current_inning: number
  is_top_inning: boolean
  state_data: Record<string, unknown>
}

export interface PitcherChangedPayload {
  type: 'PITCHER_CHANGED'
  message: string
  state_data?: Record<string, unknown>
  [key: string]: unknown
}

export interface PitcherChangeAcknowledgedPayload {
  type: 'PITCHER_CHANGE_ACKNOWLEDGED'
  message: string
  [key: string]: unknown
}

export interface GameErrorPayload {
  type: 'ERROR'
  message: string
}

export type GameSocketMessage =
  | InitGameStatePayload
  | PitchCommittedPayload
  | PlayResolvedPayload
  | StealResolvedPayload
  | PitcherChangedPayload
  | PitcherChangeAcknowledgedPayload
  | GameErrorPayload

export interface PlayResultResponse {
  event: string
  description: string
  outs: number
  balls: number
  strikes: number
  score_home: number
  score_away: number
  current_inning: number
  is_top_inning: boolean
  state_data?: Record<string, unknown> | null
}

export interface BoxScoreResponse {
  game_id: string
  final_score: { home: number; away: number }
  box_score: Record<string, unknown>
}
