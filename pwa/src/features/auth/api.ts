import { http } from '@/shared/api/client'
import type {
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserProfileResponse,
} from '@/shared/api/types'

export function login(username: string, password: string): Promise<LoginResponse> {
  const body = new URLSearchParams({ username, password })
  return http
    .post<LoginResponse>('/api/v1/auth/login', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    .then((response) => response.data)
}

export function register(payload: RegisterRequest): Promise<RegisterResponse> {
  return http
    .post<RegisterResponse>('/api/v1/auth/register', payload)
    .then((response) => response.data)
}

export function getProfile(): Promise<UserProfileResponse> {
  return http.get<UserProfileResponse>('/api/v1/user/me/profile').then((response) => response.data)
}
