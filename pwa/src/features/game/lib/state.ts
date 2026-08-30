import type {
  GameStateWS,
  InitGameStatePayload,
  PlayResolvedPayload,
  StealResolvedPayload,
} from '@/shared/api/types'

export type StateSourcePayload =
  | InitGameStatePayload
  | PlayResolvedPayload
  | StealResolvedPayload

export function parseStateData(payload: StateSourcePayload): GameStateWS {
  const stateData = payload.state_data ?? {}
  const runners = (stateData.runners ?? { '1b': null, '2b': null, '3b': null }) as Record<
    string,
    string | null
  >

  return {
    gameId: 'game_id' in payload ? payload.game_id : '',
    currentInning: payload.current_inning,
    isTopInning: payload.is_top_inning,
    homeScore: payload.score_home,
    awayScore: payload.score_away,
    balls: payload.balls,
    strikes: payload.strikes,
    outs: payload.outs,
    runners: {
      b1: runners['1b'] ?? null,
      b2: runners['2b'] ?? null,
      b3: runners['3b'] ?? null,
    },
    totalInnings: (stateData.total_innings as number | undefined) ?? 9,
    activePitcherId: stateData.active_pitcher as string | undefined,
    activeBatterId: stateData.active_batter as string | undefined,
    isGameOver: Boolean(stateData.is_game_over),
    winnerMessage: stateData.winner_message as string | undefined,
    rivalTeamName: stateData.rival_team_name as string | undefined,
    userRole: (stateData.user_role as 'HOME' | 'AWAY' | undefined) ?? 'HOME',
    state_data: stateData,
    pitcher_strikeouts: 'pitcher_strikeouts' in payload ? payload.pitcher_strikeouts : undefined,
    batter_stats: 'batter_stats' in payload ? payload.batter_stats : undefined,
    homeHits: 'home_hits' in payload && payload.home_hits != null ? payload.home_hits : undefined,
    awayHits: 'away_hits' in payload && payload.away_hits != null ? payload.away_hits : undefined,
    inning_runs: 'inning_runs' in payload ? payload.inning_runs : undefined,
    active_pitcher: 'active_pitcher' in payload ? payload.active_pitcher : undefined,
    active_batter: 'active_batter' in payload ? payload.active_batter : undefined,
    inning_completed: 'inning_completed' in payload ? payload.inning_completed : undefined,
  }
}

export function isPlayResultPayload(
  payload: unknown,
): payload is PlayResolvedPayload | StealResolvedPayload {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    ((payload as { type?: string }).type === 'PLAY_RESOLVED' ||
      (payload as { type?: string }).type === 'STEAL_RESOLVED')
  )
}