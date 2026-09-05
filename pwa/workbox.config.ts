import type { RuntimeCaching } from 'workbox-build'

export const PRECACHE_GLOB_PATTERNS = ['**/*.{js,css,html,svg,png,avif,woff2}']

export const PRECACHE_GLOB_IGNORES = [
  '**/.DS_Store',
  '**/ChatGPT Image*.png',
  'logo.png',
  'login-background.png',
  'start-*.png',
  'stadium-*.png',
  'open-pack*.png',
]

const PUBLIC_API_PATHS = [
  /^\/api\/v1\/teams\/cpu\/?$/,
  /^\/api\/v1\/cards\/[^/]+\/?$/,
]

export function isPublicApiRead(request: Request, url: URL): boolean {
  return request.method === 'GET' && PUBLIC_API_PATHS.some((pattern) => pattern.test(url.pathname))
}

export function isCacheableImage(request: Request): boolean {
  return request.method === 'GET' && request.destination === 'image'
}

export function isCacheableFont(request: Request): boolean {
  return request.method === 'GET' && request.destination === 'font'
}

export const runtimeCaching: RuntimeCaching[] = [
  {
    urlPattern: ({ request, url }) =>
      request.method === 'GET' &&
      (/^\/api\/v1\/teams\/cpu\/?$/.test(url.pathname) ||
        /^\/api\/v1\/cards\/[^/]+\/?$/.test(url.pathname)),
    method: 'GET',
    handler: 'NetworkFirst',
    options: {
      cacheName: 'public-api-v1',
      networkTimeoutSeconds: 4,
      cacheableResponse: { statuses: [200] },
      expiration: {
        maxEntries: 60,
        maxAgeSeconds: 60 * 60,
        purgeOnQuotaError: true,
      },
    },
  },
  {
    urlPattern: ({ request, url }) =>
      request.method === 'GET' &&
      request.destination === 'style' &&
      url.origin === 'https://fonts.googleapis.com',
    method: 'GET',
    handler: 'StaleWhileRevalidate',
    options: {
      cacheName: 'google-font-styles-v1',
      cacheableResponse: { statuses: [0, 200] },
      expiration: {
        maxEntries: 6,
        maxAgeSeconds: 60 * 60 * 24 * 30,
        purgeOnQuotaError: true,
      },
    },
  },
  {
    urlPattern: ({ request }) => request.method === 'GET' && request.destination === 'image',
    method: 'GET',
    handler: 'CacheFirst',
    options: {
      cacheName: 'runtime-images-v1',
      cacheableResponse: { statuses: [0, 200] },
      expiration: {
        maxEntries: 80,
        maxAgeSeconds: 60 * 60 * 24 * 30,
        purgeOnQuotaError: true,
      },
    },
  },
  {
    urlPattern: ({ request, url }) =>
      request.method === 'GET' &&
      request.destination === 'font' &&
      url.origin === 'https://fonts.gstatic.com',
    method: 'GET',
    handler: 'CacheFirst',
    options: {
      cacheName: 'runtime-fonts-v1',
      cacheableResponse: { statuses: [0, 200] },
      expiration: {
        maxEntries: 12,
        maxAgeSeconds: 60 * 60 * 24 * 365,
        purgeOnQuotaError: true,
      },
    },
  },
]
