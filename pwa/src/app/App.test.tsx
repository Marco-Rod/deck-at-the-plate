import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App', () => {
  it('renderiza la pantalla de autenticación en la ruta inicial', async () => {
    render(<App />)

    expect(await screen.findByText('Autenticación')).toBeVisible()
  })
})
