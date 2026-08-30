import { describe, expect, it } from 'vitest'
import { validateLogin, validateRegister } from './validation'

describe('validateLogin', () => {
  it('rechaza username corto', () => {
    const errors = validateLogin({ username: 'ab', password: '123456' })
    expect(errors.username).toBe('auth.error.username_short')
  })

  it('rechaza username de más de 30 caracteres', () => {
    const errors = validateLogin({ username: 'x'.repeat(31), password: '123456' })
    expect(errors.username).toBe('auth.error.username_long')
  })

  it('rechaza contraseña corta', () => {
    const errors = validateLogin({ username: 'abc', password: '123' })
    expect(errors.password).toBe('auth.error.password_short')
  })

  it('recorta espacios del username', () => {
    const errors = validateLogin({ username: '  abc  ', password: '123456' })
    expect(errors.username).toBeUndefined()
  })

  it('acepta credenciales válidas', () => {
    const errors = validateLogin({ username: 'Bateador33', password: 'secreto' })
    expect(errors).toEqual({})
  })
})

describe('validateRegister', () => {
  it('exige confirmar la contraseña', () => {
    const errors = validateRegister({ username: 'abc', password: '123456' })
    expect(errors.confirmPassword).toBe('auth.error.confirm_required')
  })

  it('detecta contraseñas distintas', () => {
    const errors = validateRegister({
      username: 'abc',
      password: '123456',
      confirmPassword: '654321',
    })
    expect(errors.confirmPassword).toBe('auth.error.password_mismatch')
  })

  it('acepta un registro válido', () => {
    const errors = validateRegister({
      username: 'abc',
      password: '123456',
      confirmPassword: '123456',
    })
    expect(errors).toEqual({})
  })
})
