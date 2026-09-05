import { describe, expect, it } from 'vitest'
import {
  PRECACHE_GLOB_IGNORES,
  PRECACHE_GLOB_PATTERNS,
  isCacheableFont,
  isCacheableImage,
  isPublicApiRead,
  runtimeCaching,
} from './workbox.config'

function request(path: string, method = 'GET'): Request {
  return new Request(`https://game.example${path}`, { method })
}

describe('Workbox runtime caching', () => {
  it('precachea el app shell y excluye los fondos PNG duplicados', () => {
    expect(PRECACHE_GLOB_PATTERNS).toContain('**/*.{js,css,html,svg,png,avif,woff2}')
    expect(PRECACHE_GLOB_IGNORES).toEqual(
      expect.arrayContaining([
        'logo.png',
        'login-background.png',
        'start-*.png',
        'stadium-*.png',
        'open-pack*.png',
      ]),
    )
  })

  it('usa Network First solamente para lecturas públicas permitidas', () => {
    expect(isPublicApiRead(request('/api/v1/teams/cpu'), new URL('https://game.example/api/v1/teams/cpu'))).toBe(true)
    expect(isPublicApiRead(request('/api/v1/cards/card-1'), new URL('https://game.example/api/v1/cards/card-1'))).toBe(true)
    expect(isPublicApiRead(request('/api/v1/user/me/profile'), new URL('https://game.example/api/v1/user/me/profile'))).toBe(false)
    expect(isPublicApiRead(request('/api/v1/teams/cpu', 'POST'), new URL('https://game.example/api/v1/teams/cpu'))).toBe(false)

    expect(runtimeCaching[0]).toMatchObject({
      method: 'GET',
      handler: 'NetworkFirst',
      options: { cacheName: 'public-api-v1', networkTimeoutSeconds: 4 },
    })
  })

  it('no cachea mutaciones ni respuestas privadas mediante ninguna regla de API', () => {
    const apiRule = runtimeCaching[0]
    expect(apiRule?.method).toBe('GET')
    expect(isPublicApiRead(request('/api/v1/user/me/lineup', 'PUT'), new URL('https://game.example/api/v1/user/me/lineup'))).toBe(false)
    expect(isPublicApiRead(request('/api/v1/games/game-1'), new URL('https://game.example/api/v1/games/game-1'))).toBe(false)
  })

  it('limita y expira los caches de imágenes y fuentes', () => {
    const imageRequest = request('/stadium.avif')
    Object.defineProperty(imageRequest, 'destination', { value: 'image' })
    const fontRequest = request('/font.woff2')
    Object.defineProperty(fontRequest, 'destination', { value: 'font' })

    expect(isCacheableImage(imageRequest)).toBe(true)
    expect(isCacheableFont(fontRequest)).toBe(true)
    expect(runtimeCaching[1]).toMatchObject({
      handler: 'StaleWhileRevalidate',
      options: { cacheName: 'google-font-styles-v1', expiration: { maxEntries: 6 } },
    })
    expect(runtimeCaching[2]).toMatchObject({
      handler: 'CacheFirst',
      options: { expiration: { maxEntries: 80, purgeOnQuotaError: true } },
    })
    expect(runtimeCaching[3]).toMatchObject({
      handler: 'CacheFirst',
      options: {
        cacheName: 'runtime-fonts-v1',
        expiration: { maxEntries: 12, purgeOnQuotaError: true },
      },
    })
  })
})
