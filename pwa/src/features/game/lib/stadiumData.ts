import type { BatterSummary, PitcherSummary } from '../components/stadium/playerPanelTypes'
import type {
  GameStateWS,
  PlayerCard,
  PlayerGameData,
  PlayerRole,
  PlayerStat,
} from '@/shared/api/types'

export interface IntroPlayer {
  name: string
  number: string
  photo?: string
  overall?: number
  position?: string
}

function statValue(stats: PlayerStat[] | undefined, labels: string[], fallback = 0): number {
  const found = stats?.find((stat) => labels.includes(stat.label.toUpperCase()))
  return found?.val ?? fallback
}

export function toPitcherSummary(player?: PlayerGameData): PitcherSummary {
  if (!player)
    return {
      id: '',
      name: 'LANZADOR',
      number: '0',
      overall: 0,
      velocity: 0,
      control: 0,
      movement: 0,
      stamina: 0,
      pitchCount: 0,
      rarity: 'COMMON',
      repertoire: null,
    }
  const stamina =
    player.fatigue_level == null
      ? statValue(player.stats, ['STAM', 'STAMINA'], 100)
      : 100 - player.fatigue_level
  return {
    id: player.id,
    name: player.name,
    number: player.number,
    overall: player.overall,
    velocity: statValue(player.stats, ['VEL', 'VELO', 'VELOCITY']),
    control: statValue(player.stats, ['CTRL', 'CONTROL']),
    movement: statValue(player.stats, ['MOV', 'MOVEMENT']),
    stamina: Math.round(Math.min(100, Math.max(0, stamina))),
    pitchCount: player.pitch_count ?? 0,
    rarity: player.rarity ?? 'COMMON',
    repertoire: player.repertoire ?? null,
  }
}

export function toBatterSummary(player?: PlayerGameData): BatterSummary {
  if (!player)
    return {
      id: '',
      name: 'BATEADOR',
      number: '0',
      overall: 0,
      contact: 0,
      power: 0,
      speed: 0,
      rarity: 'COMMON',
    }
  return {
    id: player.id,
    name: player.name,
    number: player.number,
    overall: player.overall,
    contact: statValue(player.stats, ['CON', 'CONTACT']),
    power: statValue(player.stats, ['POW', 'POWER']),
    speed: statValue(player.stats, ['SPD', 'SPEED']),
    rarity: player.rarity ?? 'COMMON',
  }
}

export function toGamePlayer(card: PlayerCard, role: PlayerRole): PlayerGameData {
  const stats: PlayerStat[] = [
    { label: 'VEL', val: card.velocity },
    { label: 'CTRL', val: card.control },
    { label: 'MOV', val: card.movement },
    { label: 'CON', val: card.contact },
    { label: 'POW', val: card.power },
  ]
  if (card.position !== 'P' && card.position !== 'SP')
    stats.push({ label: 'SPD', val: Math.round((card.contact + card.power) / 2) })
  return {
    id: card.id,
    name: card.name,
    number: card.number,
    overall: card.overall,
    position: card.position,
    photo: '',
    role,
    rarity: card.rarity,
    repertoire: card.repertoire ?? undefined,
    stats,
  }
}

export function resolveRole(userRole: 'HOME' | 'AWAY', isTop: boolean): PlayerRole {
  return userRole === 'HOME' ? (isTop ? 'PITCHER' : 'BATTER') : isTop ? 'BATTER' : 'PITCHER'
}

export function extractLineupIds(state: GameStateWS | null, userRole: 'HOME' | 'AWAY') {
  const data = (state?.state_data ?? {}) as Record<string, unknown>
  const home = Array.isArray(data.home_lineup) ? (data.home_lineup as string[]) : []
  const away = Array.isArray(data.away_lineup) ? (data.away_lineup as string[]) : []
  return userRole === 'HOME' ? { user: home, cpu: away } : { user: away, cpu: home }
}

export function extractTacticalHand(
  state: GameStateWS | null,
  userRole: 'HOME' | 'AWAY',
): string[] {
  const data = (state?.state_data ?? {}) as Record<string, unknown>
  const tactics = (data.tactics ?? {}) as Record<string, { hand?: unknown }>
  const hand = tactics[userRole === 'HOME' ? 'home' : 'away']?.hand
  return Array.isArray(hand) ? (hand as string[]) : []
}

export function extractNextBatterId(state: GameStateWS | null): string | null {
  if (!state) return null
  const data = (state.state_data ?? {}) as Record<string, unknown>
  const lineup = data[state.isTopInning ? 'away_lineup' : 'home_lineup']
  const index = data[state.isTopInning ? 'away_batter_index' : 'home_batter_index']
  if (!Array.isArray(lineup) || lineup.length === 0) return null
  return lineup[((typeof index === 'number' ? index : 0) + 1) % lineup.length] as string
}

export function toIntroPlayer(card: PlayerCard): IntroPlayer {
  return { name: card.name, number: card.number, overall: card.overall, position: card.position }
}
