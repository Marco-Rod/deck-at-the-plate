/**
 * useStadiumSocket — Hook de comunicación WebSocket con el backend
 * =================================================================
 * Gestiona la conexión en tiempo real con el servidor de juego y expone
 * el estado del partido y las funciones para enviar acciones vía REST.
 *
 * Flujo de comunicación:
 *   - La conexión WS es unidireccional desde el servidor: solo recibe eventos.
 *   - Las acciones del jugador (pitch, swing, tácticas) se envían vía REST
 *     usando los helpers de api.js.
 *   - El servidor emite los siguientes eventos:
 *       INIT_GAME_STATE   → Estado inicial al conectarse.
 *       PITCH_COMMITTED   → El lanzador registró su picheo.
 *       PLAY_RESOLVED     → El at-bat se resolvió con su resultado.
 *       STEAL_RESOLVED    → Un intento de robo fue resuelto.
 *
 * URL del WebSocket:
 *   ws://<host>/ws/games/<gameId>/<userId>
 *
 * Parámetros:
 *   gameId  — ID de la sesión de juego (ej. "game_a1b2c3d4")
 *   userId  — ID del usuario autenticado (para Fog of War en el servidor)
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import {
  GameStateWS,
  PitchType,
  PlayResolvedPayload,
  PitchCommittedPayload,
} from '../types/stadium';
import { games as gamesApi } from '../utils/api';

interface PitchPayload {
  pitch_type: PitchType;
  zone: number;
}

interface SwingPayload {
  swing_type: 'NORMAL' | 'POWER' | 'TAKE' | 'BUNT';
  guessed_zone: number | null;
  guessed_pitch: PitchType | null;
}

interface UseStadiumSocketReturn {
  gameState: GameStateWS | null;
  lastResult: string | null;
  hasPitched: boolean;
  isConnected: boolean;
  sendPitch: (zone: number, pitchType: PitchType) => Promise<void>;
  sendSwing: (swingType: SwingPayload['swing_type'], guessedZone: number | null, guessedPitch: PitchType | null) => Promise<void>;
  sendTactic: (tacticId: string, playerRole: 'PITCHER' | 'BATTER') => Promise<void>;
}

/**
 * Convierte el payload de PLAY_RESOLVED del backend al formato GameStateWS del frontend.
 */
function mapPayloadToGameState(payload: PlayResolvedPayload): GameStateWS {
  const stateData = payload.state_data as Record<string, unknown>;
  const runners = (stateData?.runners as Record<string, string | null>) || { '1b': null, '2b': null, '3b': null };

  return {
    currentInning: payload.current_inning,
    isTopInning: payload.is_top_inning,
    homeScore: payload.score_home,
    awayScore: payload.score_away,
    balls: payload.balls,
    strikes: payload.strikes,
    outs: payload.outs,
    runners: {
      b1: runners['1b'] ? runners['1b'] : null,
      b2: runners['2b'] ? runners['2b'] : null,
      b3: runners['3b'] ? runners['3b'] : null,
    },
    lastEvent: payload.event,
    isGameOver: !!(stateData?.is_game_over),
    winnerMessage: stateData?.winner_message as string | undefined,
  };
}

export const useStadiumSocket = (
  gameId: string,
  userId: string
): UseStadiumSocketReturn => {
  const [gameState, setGameState] = useState<GameStateWS | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [hasPitched, setHasPitched] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId || !userId) return;

    // URL correcta del backend: /ws/games/{game_id}/{user_id}
    const wsHost = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
      .replace(/^http/, 'ws');
    const wsUrl = `${wsHost}/ws/games/${gameId}/${userId}`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log(`[WS] Conectado a la partida ${gameId}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { type: string; [key: string]: unknown };

        switch (data.type) {
          case 'INIT_GAME_STATE': {
            // Estado inicial al conectarse — se cargará vía REST en el futuro
            console.log('[WS] INIT_GAME_STATE recibido');
            break;
          }

          case 'PITCH_COMMITTED': {
            const payload = data as unknown as PitchCommittedPayload;
            setHasPitched(payload.has_pitched);
            break;
          }

          case 'PLAY_RESOLVED': {
            const payload = data as unknown as PlayResolvedPayload;
            const newState = mapPayloadToGameState(payload);
            setGameState(newState);
            setLastResult(payload.description);
            setHasPitched(false); // El picheo ya fue procesado
            break;
          }

          case 'STEAL_RESOLVED': {
            setLastResult((data.description as string) || null);
            break;
          }

          default:
            console.warn('[WS] Tipo de evento desconocido:', data.type);
        }
      } catch (err) {
        console.error('[WS] Error parseando mensaje:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log(`[WS] Desconectado de la partida ${gameId}`);
    };

    ws.onerror = (err) => {
      console.error('[WS] Error de conexión:', err);
    };

    return () => {
      ws.close();
    };
  }, [gameId, userId]);

  /**
   * Envía el picheo del lanzador vía REST.
   * El backend guarda el picheo y emite PITCH_COMMITTED a ambos clientes.
   */
  const sendPitch = useCallback(
    async (zone: number, pitchType: PitchType): Promise<void> => {
      const payload: PitchPayload = { pitch_type: pitchType, zone };
      await gamesApi.pitch(gameId, payload);
    },
    [gameId]
  );

  /**
   * Envía el swing del bateador vía REST.
   * El backend resuelve la jugada y emite PLAY_RESOLVED a ambos clientes.
   */
  const sendSwing = useCallback(
    async (
      swingType: SwingPayload['swing_type'],
      guessedZone: number | null,
      guessedPitch: PitchType | null
    ): Promise<void> => {
      const payload: SwingPayload = {
        swing_type: swingType,
        guessed_zone: guessedZone,
        guessed_pitch: guessedPitch,
      };
      await gamesApi.swing(gameId, payload);
    },
    [gameId]
  );

  /**
   * Activa una carta táctica antes del enfrentamiento.
   */
  const sendTactic = useCallback(
    async (tacticId: string, playerRole: 'PITCHER' | 'BATTER'): Promise<void> => {
      await gamesApi.playTactic(gameId, {
        player_role: playerRole,
        tactic_id: tacticId,
      });
    },
    [gameId]
  );

  return { gameState, lastResult, hasPitched, isConnected, sendPitch, sendSwing, sendTactic };
};
