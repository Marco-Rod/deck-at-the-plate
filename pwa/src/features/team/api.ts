import { http } from '@/shared/api/client'
import type {
  CreateTeamRequest,
  Franchise,
  LineupResponse,
  TeamStatsResponse,
  UserInventoryResponse,
  UserTeam,
} from '@/shared/api/types'

export function createTeam(payload: CreateTeamRequest): Promise<UserTeam> {
  return http.post<UserTeam>('/api/v1/user/me/team', payload).then((response) => response.data)
}

export function getInventory(): Promise<UserInventoryResponse> {
  return http.get<UserInventoryResponse>('/api/v1/user/me/inventory').then((response) => response.data)
}

export function getLineup(): Promise<LineupResponse> {
  return http.get<LineupResponse>('/api/v1/user/me/lineup').then((response) => response.data)
}

export function saveLineup(payload: { name?: string; slots: Record<string, string> }): Promise<LineupResponse> {
  return http.put<LineupResponse>('/api/v1/user/me/lineup', payload).then((response) => response.data)
}

export function getTeamStats(): Promise<TeamStatsResponse> {
  return http.get<TeamStatsResponse>('/api/v1/user/me/team-stats').then((response) => response.data)
}

export function getTeam(): Promise<UserTeam> {
  return http.get<UserTeam>('/api/v1/user/me/team').then((response) => response.data)
}

export function updateBaseFranchise(baseFranchise: string): Promise<UserTeam> {
  return http
    .put<UserTeam>('/api/v1/user/me/team/franchise', { base_franchise: baseFranchise })
    .then((response) => response.data)
}

export function getCpuTeams(): Promise<Franchise[]> {
  return http.get<Franchise[]>('/api/v1/teams/cpu').then((response) => response.data)
}
