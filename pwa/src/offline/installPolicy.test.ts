import { describe, expect, it } from 'vitest'
import {
  canSuggestInstall,
  isIosDevice,
  isIosSafari,
  isStandaloneDisplay,
} from './installPolicy'

function navigatorWith(userAgent: string, maxTouchPoints = 0): Navigator {
  return { userAgent, maxTouchPoints } as Navigator
}

describe('PWA install policy', () => {
  it('detecta Safari de iOS sin confundir otros navegadores', () => {
    const safari = navigatorWith('Mozilla/5.0 (iPhone) AppleWebKit/605.1.15 Version/18 Mobile Safari/604.1')
    const chrome = navigatorWith('Mozilla/5.0 (iPhone) AppleWebKit/605.1.15 CriOS/140 Mobile Safari/604.1')

    expect(isIosDevice(safari)).toBe(true)
    expect(isIosSafari(safari)).toBe(true)
    expect(isIosSafari(chrome)).toBe(false)
  })

  it('reconoce iPad moderno y ambos modos standalone', () => {
    const ipad = navigatorWith('Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 Version/18 Safari/605.1.15', 5)
    expect(isIosSafari(ipad)).toBe(true)
    expect(isStandaloneDisplay(ipad, true)).toBe(true)
    expect(isStandaloneDisplay({ ...ipad, standalone: true }, false)).toBe(true)
    expect(isStandaloneDisplay(ipad, false)).toBe(false)
  })

  it('limita la sugerencia a rutas sin tareas críticas', () => {
    expect(canSuggestInstall('/lobby', false)).toBe(true)
    expect(canSuggestInstall('/team', false)).toBe(true)
    expect(canSuggestInstall('/onboarding', false)).toBe(false)
    expect(canSuggestInstall('/roster/pending', false)).toBe(false)
    expect(canSuggestInstall('/game/game-1', false)).toBe(false)
    expect(canSuggestInstall('/lobby', true)).toBe(false)
  })
})
