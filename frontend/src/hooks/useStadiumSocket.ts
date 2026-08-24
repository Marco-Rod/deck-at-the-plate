/**
 * useStadiumSocket — Hook de comunicación WebSocket con el backend
 * =================================================================
 * Gestiona la conexión en tiempo real con el servidor de juego y expone
 * el estado del partido y las funciones para enviar acciones vía REST.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import {
  GameStateWS,
  PitchType,
  PlayResolvedPayload,
  PitchCommittedPayload,
  InitGameStatePayload,
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

function parseStateData(payload: { current_inning: number; is_top_inning: boolean; score_home: number; score_away: number; balls: number; strikes: number; outs: number; state_data: Record<string, unknown> }): GameStateWS {
  const stateData = payload.state_data || {};
  const runners = (stateData.runners as Record<string, string | null>) || { '1b': null, '2b': null, '3b': null };

  return {
    currentInning: payload.current_inning,
    isTopInning: payload.is_top_inning,
    homeScore: payload.score_home,
    awayScore: payload.score_away,
    balls: payload.balls,
    strikes: payload.strikes,
    outs: payload.outs,
    runners: {
      b1: runners['1b'] || null,
      b2: runners['2b'] || null,
      b3: runners['3b'] || null,
    },
    activePitcherId: stateData.active_pitcher as string | undefined,
    activeBatterId: stateData.active_batter as string | undefined,
    isGameOver: !!(stateData.is_game_over),
    winnerMessage: stateData.winner_message as string | undefined,
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

    const wsHost = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
      .replace(/^http/, 'ws');
    const wsUrl = `${wsHost}/ws/games/${gameId}/${userId}`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log(`[WS] Conectado exitosamente a ${gameId}`);
    };

    ws.onmessage = (event) => {
  try {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case 'INIT_GAME_STATE': {
        const payload = data as InitGameStatePayload;
        setGameState(parseStateData(payload));
        break;
      }

      case 'PITCH_COMMITTED': {
        const payload = data as PitchCommittedPayload;
        // Solo actualizamos que ya se realizó el picheo (para habilitar el botón del bateador)
        setHasPitched(payload.has_pitched);
        break;
      }

      case 'PLAY_RESOLVED': {
        const payload = data as PlayResolvedPayload;
        setGameState(parseStateData(payload));
        // Solo asignamos a lastResult el resultado real de la jugada (ej: "HIT 1B", "OUT", etc.)
        setLastResult(payload.description);
        setHasPitched(false);
        break;
      }

      case 'STEAL_RESOLVED': {
        setLastResult((data.description as string) || null);
        break;
      }

      default:
        console.warn('[WS] Evento no manejado:', data.type);
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
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [gameId, userId]);

  const sendPitch = useCallback(
    async (zone: number, pitchType: PitchType): Promise<void> => {
      const payload: PitchPayload = { pitch_type: pitchType, zone };
      await gamesApi.pitch(gameId, payload);
    },
    [gameId]
  );

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