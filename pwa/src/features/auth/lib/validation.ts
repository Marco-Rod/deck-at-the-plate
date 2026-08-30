export type AuthMode = 'login' | 'register'

export interface AuthFormValues {
  username: string
  password: string
  confirmPassword?: string
}

export type AuthFieldKey = 'username' | 'password' | 'confirmPassword'

export type AuthFieldErrors = Partial<Record<AuthFieldKey, string>>

export const USERNAME_MIN = 3
export const USERNAME_MAX = 30
export const PASSWORD_MIN = 6

export function validateUsername(username: string): string | undefined {
  const value = username.trim()
  if (value.length < USERNAME_MIN) return 'auth.error.username_short'
  if (value.length > USERNAME_MAX) return 'auth.error.username_long'
  return undefined
}

export function validatePassword(password: string): string | undefined {
  if (password.length < PASSWORD_MIN) return 'auth.error.password_short'
  return undefined
}

export function validateLogin(values: AuthFormValues): AuthFieldErrors {
  const errors: AuthFieldErrors = {}
  const usernameError = validateUsername(values.username)
  if (usernameError) errors.username = usernameError
  const passwordError = validatePassword(values.password)
  if (passwordError) errors.password = passwordError
  return errors
}

export function validateRegister(values: AuthFormValues): AuthFieldErrors {
  const errors = validateLogin(values)
  if (!values.confirmPassword) {
    errors.confirmPassword = 'auth.error.confirm_required'
  } else if (values.confirmPassword !== values.password) {
    errors.confirmPassword = 'auth.error.password_mismatch'
  }
  return errors
}
