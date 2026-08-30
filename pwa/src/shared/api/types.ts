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
}
