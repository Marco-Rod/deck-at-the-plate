import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), 'utf8')
}

describe('media loading policy', () => {
  it('prioriza fondos LCP únicamente dentro de su pantalla', () => {
    const auth = source('src/features/auth/pages/AuthPage.tsx')
    const intro = source('src/features/game/components/modals/GameIntroModal.tsx')
    const onboarding = source('src/features/onboarding/pages/OnboardingPage.tsx')

    expect(auth).toMatch(/rel="preload"[\s\S]*login-background\.avif[\s\S]*fetchPriority="high"/)
    expect(intro).toMatch(/start-mobile\.avif[\s\S]*media="\(max-width: 1199px\)"/)
    expect(intro).toMatch(/start-desktop\.avif[\s\S]*media="\(min-width: 1200px\)"/)
    expect(onboarding).toMatch(/open-pack-mobile\.avif[\s\S]*media="\(max-width: 767px\)"/)
    expect(onboarding).toMatch(/open-pack\.avif[\s\S]*media="\(min-width: 768px\)"/)
  })

  it('reserva dimensiones y difiere la imagen repetida de las cartas', () => {
    const cardBack = source('src/features/onboarding/components/PlayerCardBack.tsx')
    expect(cardBack).toMatch(/width="128"[\s\S]*height="128"[\s\S]*loading="lazy"/)

    const auth = source('src/features/auth/pages/AuthPage.tsx')
    expect(auth).toMatch(/logo-mark-128\.avif[\s\S]*logo-mark\.png/)
    expect(auth).toMatch(/logo-mark\.png[\s\S]*width="128"[\s\S]*height="128"/)
  })

  it('solo monta y precarga el audio cuando la introducción es visible', () => {
    const stadium = source('src/features/game/pages/StadiumPage.tsx')
    expect(stadium).toMatch(/isIntroVisible \? \([\s\S]*playball-stadium\.mp3[\s\S]*preload="auto"/)
  })
})
