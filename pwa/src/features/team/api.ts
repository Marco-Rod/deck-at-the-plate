import { http } from '@/shared/api/client'
import type { CreateTeamRequest, Franchise, UserTeam } from '@/shared/api/types'

export function createTeam(payload: CreateTeamRequest): Promise<UserTeam> {
  return http.post<UserTeam>('/api/v1/user/me/team', payload).then((response) => response.data)
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
