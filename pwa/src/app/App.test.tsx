import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'
import { Providers } from './providers'

describe('App', () => {
  it('renderiza la pantalla de autenticación en la ruta inicial', async () => {
    render(
      <Providers>
        <App />
      </Providers>,
    )

    expect(await screen.findByRole('heading', { name: /deck at the plate/i })).toBeVisible()
  })
})
