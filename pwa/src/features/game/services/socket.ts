import { buildGameWsUrl } from '@/shared/api/config'
import { getGameState } from '@/features/game/api'
import type { GameConnectionMode, GameSocketMessage, InitGameStatePayload } from '@/shared/api/types'

export type SocketMessageHandler = (message: GameSocketMessage) => void
export type ConnectionStatusHandler = (connected: boolean, mode: GameConnectionMode) => void

const MAX_RECONNECT_ATTEMPTS = 8
const POLL_INTERVAL_MS = 2000

function backoffDelay(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, 30000)
}

export class GameSocketClient {
  private gameId = ''
  private token = ''
  private ws: WebSocket | null = null
  private statusHandler: ConnectionStatusHandler | null = null
  private messageHandler: SocketMessageHandler | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pollTimer: ReturnType<typeof setInterval> | null = null
  private reconnectAttempt = 0
  private mode: GameConnectionMode = 'ws'
  private started = false
  private lastSentStatus: { connected: boolean; mode: GameConnectionMode } | null = null

  connect(gameId: string, token: string, handlers: {
    onMessage: SocketMessageHandler
    onStatus?: ConnectionStatusHandler
  }): void {
    this.teardown()
    this.gameId = gameId
    this.token = token
    this.messageHandler = handlers.onMessage
    this.statusHandler = handlers.onStatus ?? null
    this.reconnectAttempt = 0
    this.mode = 'ws'
    this.started = true
    this.openWebSocket()
  }

  disconnect(): void {
    this.started = false
    this.teardown()
  }

  private teardown(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onclose = null
      this.ws.onerror = null
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close()
      } else if (this.ws.readyState === WebSocket.CONNECTING) {
        // Cerrar un socket en CONNECTING dispara la advertencia
        // "WebSocket is closed before the connection is established".
        // Esperamos a que complete el handshake y lo cerramos en onopen
        // para evitarla sin filtrar la conexión.
        const ws = this.ws
        ws.onopen = () => {
          ws.close()
        }
      }
      this.ws = null
    }
  }

  private openWebSocket(): void {
    if (!this.started) return
    const ws = new WebSocket(buildGameWsUrl(this.gameId, this.token))
    this.ws = ws

    ws.onopen = () => {
      if (!this.started) {
        ws.close()
        return
      }
      this.reconnectAttempt = 0
      this.setMode('ws')
      this.emitStatus(true)
      this.stopPolling()
    }

    ws.onmessage = (event) => {
      if (!this.started) return
      try {
        const data = JSON.parse(event.data as string) as GameSocketMessage
        this.messageHandler?.(data)
      } catch (err) {
        console.error('[WS] Error parseando mensaje:', err)
      }
    }

    ws.onclose = () => {
      this.emitStatus(false)
      if (!this.started) return
      this.scheduleReconnect()
    }

    ws.onerror = () => {
      ws.close()
    }
  }

  private scheduleReconnect(): void {
    if (!this.started || this.reconnectTimer) return

    if (this.reconnectAttempt >= MAX_RECONNECT_ATTEMPTS) {
      this.startPolling()
      return
    }

    const delay = backoffDelay(this.reconnectAttempt)
    this.reconnectAttempt += 1

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.openWebSocket()
    }, delay)
  }

  private startPolling(): void {
    if (!this.started) return
    if (this.mode === 'polling') return
    this.setMode('polling')
    this.emitStatus(false)

    const pollOnce = async () => {
      if (!this.started || this.mode !== 'polling') return
      try {
        const state = await getGameState(this.gameId)
        if (!this.started || this.mode !== 'polling') return
        const payload: InitGameStatePayload = {
          type: 'INIT_GAME_STATE',
          game_id: this.gameId,
          outs: state.outs,
          balls: state.balls,
          strikes: state.strikes,
          score_home: state.score_home,
          score_away: state.score_away,
          current_inning: state.current_inning,
          is_top_inning: state.is_top_inning,
          state_data: { ...(state.state_data ?? {}), user_role: undefined },
        }
        this.messageHandler?.(payload)
      } catch (err) {
        console.error('[WS] Polling fallback error:', err)
      }
    }

    void pollOnce()
    this.pollTimer = setInterval(() => void pollOnce(), POLL_INTERVAL_MS)
  }

  private stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
  }

  private setMode(mode: GameConnectionMode): void {
    this.mode = mode
  }

  private emitStatus(connected: boolean): void {
    const current = { connected, mode: this.mode }
    if (
      this.lastSentStatus &&
      this.lastSentStatus.connected === current.connected &&
      this.lastSentStatus.mode === current.mode
    ) {
      return
    }
    this.lastSentStatus = current
    this.statusHandler?.(connected, this.mode)
  }
}

export const gameSocketClient = new GameSocketClient()