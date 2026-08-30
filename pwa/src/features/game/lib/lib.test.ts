import { describe, expect, it } from 'vitest'
import { normalizeEventName } from './eventNormalizer'
import { parseStateData } from './state'

describe('normalizeEventName', () => {
  it.each([
    ['HOME RUN', 'HOME_RUN'],
    ['ground out', 'OUT_GROUND'],
    ['STRIKE-LOOKING', 'STRIKE_LOOKING'],
    ['K', 'STRIKEOUT'],
    ['1B', 'HIT_1B'],
    ['DOUBLE PLAY', 'DOUBLE_PLAY'],
    ['BB', 'WALK'],
  ])('normaliza %s → %s', (input, expected) => {
    expect(normalizeEventName(input)).toBe(expected)
  })

  it('deja intactas las claves estándar', () => {
    expect(normalizeEventName('HOME_RUN')).toBe('HOME_RUN')
    expect(normalizeEventName('GAME_OVER')).toBe('GAME_OVER')
  })

  it('convierte espacios a guiones bajos para eventos desconocidos', () => {
    expect(normalizeEventName('wild pitch')).toBe('WILD_PITCH')
  })

  it('retorna vacío si no hay evento', () => {
    expect(normalizeEventName('')).toBe('')
  })
})

describe('parseStateData', () => {
  const basePayload = {
    type: 'PLAY_RESOLVED' as const,
    event: 'HOME_RUN',
    description: 'Jonrón',
    outs: 2,
    balls: 1,
    strikes: 2,
    score_home: 3,
    score_away: 0,
    current_inning: 4,
    is_top_inning: true,
    state_data: {
      runners: { '1b': 'card_1', '2b': null, '3b': null },
      total_innings: 9,
      active_pitcher: 'pitcher_1',
      active_batter: 'batter_1',
      is_game_over: false,
      rival_team_name: 'Dodgers',
      user_role: 'HOME',
    },
  }

  it('normaliza el payload a GameStateWS', () => {
    const state = parseStateData(basePayload)

    expect(state.currentInning).toBe(4)
    expect(state.isTopInning).toBe(true)
    expect(state.homeScore).toBe(3)
    expect(state.awayScore).toBe(0)
    expect(state.balls).toBe(1)
    expect(state.strikes).toBe(2)
    expect(state.outs).toBe(2)
    expect(state.runners).toEqual({ b1: 'card_1', b2: null, b3: null })
    expect(state.totalInnings).toBe(9)
    expect(state.activePitcherId).toBe('pitcher_1')
    expect(state.activeBatterId).toBe('batter_1')
    expect(state.userRole).toBe('HOME')
    expect(state.isGameOver).toBe(false)
    expect(state.rivalTeamName).toBe('Dodgers')
  })

  it('no necesita runners ni total_innings (usa defaults)', () => {
    const state = parseStateData({
      type: 'INIT_GAME_STATE',
      game_id: 'game_1',
      outs: 0,
      balls: 0,
      strikes: 0,
      score_home: 0,
      score_away: 0,
      current_inning: 1,
      is_top_inning: true,
      state_data: { user_role: 'AWAY' },
    })

    expect(state.gameId).toBe('game_1')
    expect(state.runners).toEqual({ b1: null, b2: null, b3: null })
    expect(state.totalInnings).toBe(9)
    expect(state.userRole).toBe('AWAY')
  })
})