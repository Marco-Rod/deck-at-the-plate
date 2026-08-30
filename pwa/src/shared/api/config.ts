export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function buildGameWsUrl(gameId: string, token: string): string {
  const base = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/^http/, 'ws')
  return `${base}/ws/games/${gameId}?token=${encodeURIComponent(token)}`
}
