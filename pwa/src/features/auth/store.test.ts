import { beforeEach, describe, expect, it } from 'vitest'
import { selectIsAuthenticated, useAuthStore } from './store'

const loginPayload = {
  access_token: 'jwt-token',
  token_type: 'bearer',
  user_id: 'usr-1',
  username: 'Bateador33',
}

beforeEach(() => {
  useAuthStore.persist.clearStorage()
  useAuthStore.setState({ token: null, user: null })
})

describe('useAuthStore', () => {
  it('signIn guarda el token y el usuario', () => {
    useAuthStore.getState().signIn(loginPayload)

    const state = useAuthStore.getState()
    expect(state.token).toBe('jwt-token')
    expect(state.user).toEqual({ userId: 'usr-1', username: 'Bateador33' })
    expect(selectIsAuthenticated(state)).toBe(true)
  })

  it('signOut limpia la sesión', () => {
    useAuthStore.getState().signIn(loginPayload)
    useAuthStore.getState().signOut()

    const state = useAuthStore.getState()
    expect(state.token).toBeNull()
    expect(state.user).toBeNull()
    expect(selectIsAuthenticated(state)).toBe(false)
  })
})
