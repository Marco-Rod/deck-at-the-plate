import '@/shared/lib/i18n'
import { act, render, waitFor } from '@testing-library/react'
import i18n from 'i18next'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { getRouteTitleKey, useRouteMetadata } from './useRouteMetadata'

function MetadataHarness() {
  useRouteMetadata()
  return null
}

afterEach(async () => {
  await act(() => i18n.changeLanguage('es'))
  document.title = ''
})

describe('route metadata', () => {
  it('recognizes dynamic game and roster routes', () => {
    expect(getRouteTitleKey('/game/game_123')).toBe('meta.game')
    expect(getRouteTitleKey('/roster/pending')).toBe('meta.roster')
    expect(getRouteTitleKey('/unknown')).toBeNull()
  })

  it('synchronizes the localized title and document language', async () => {
    await act(() => i18n.changeLanguage('es'))
    render(
      <MemoryRouter initialEntries={['/game/game_123']}>
        <MetadataHarness />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(document.title).toBe('Partido | Deck at the Plate')
      expect(document.documentElement.lang).toBe('es')
    })

    await act(() => i18n.changeLanguage('en'))

    await waitFor(() => {
      expect(document.title).toBe('Game | Deck at the Plate')
      expect(document.documentElement.lang).toBe('en')
    })
  })
})
