/**
 * useStadiumSocket — Hook de comunicación WebSocket con el backend
 * =================================================================
 * Gestiona la conexión en tiempo real con el servidor de juego.
 * 
 * Cambio en Fase 1 (Event Sequencer):
 * - Ya NO actualiza state directamente en eventos
 * - En su lugar, llama callbacks para que el padre (StadiumShowcaseScreen)
 *   enquee los eventos en el useEventSequencer
 * - Mantiene INIT_GAME_STATE como excepción (sin sequencer)
 * - PITCH_COMMITTED es inmediato (no necesita sequencer)
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

/**
 * Callbacks opcionales para eventos del WebSocket
 * Permiten que el parent component (StadiumShowcaseScreen) controle cómo
 * procesar cada evento usando el useEventSequencer
 */
interface WebSocketCallbacks {
  onPlayResolved?: (payload: PlayResolvedPayload) => void;
  onPitcherChanged?: (payload: any) => void;
  onGameStateInit?: (payload: InitGameStatePayload) => void;
}

interface UseStadiumSocketReturn {
  gameState: GameStateWS | null;
  hasPitched: boolean;
  isConnected: boolean;
  sendPitch: (zone: number, pitchType: PitchType) => Promise<void>;
  sendSwing: (swingType: SwingPayload['swing_type'], guessedZone: number | null, guessedPitch: PitchType | null) => Promise<void>;
  sendTactic: (tacticId: string, playerRole: 'PITCHER' | 'BATTER') => Promise<void>;
}

function parseStateData(payload: { current_inning: number; is_top_inning: boolean; score_home: number; score_away: number; balls: number; strikes: number; outs: number; state_data: Record<string, unknown>; pitcher_strikeouts?: Record<string, number>; batter_stats?: Record<string, any>; home_hits?: number; away_hits?: number; inning_runs?: Record<string, number>; active_pitcher?: any; active_batter?: any }): GameStateWS {
  const stateData = payload.state_data || {};
  const runners = (stateData.runners as Record<string, string | null>) || { '1b': null, '2b': null, '3b': null };

  console.log('⭐ [PARSE_STATE_DATA] pitcher_strikeouts:', payload.pitcher_strikeouts);
  console.log('⭐ [PARSE_STATE_DATA] batter_stats keys:', Object.keys(payload.batter_stats || {}));
  console.log('⭐ [PARSE_STATE_DATA] hits:', { home_hits: payload.home_hits, away_hits: payload.away_hits });
  console.log('⭐ [PARSE_STATE_DATA] active_pitcher rarity:', payload.active_pitcher?.rarity);
  console.log('⭐ [PARSE_STATE_DATA] active_batter rarity:', payload.active_batter?.rarity);

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
    totalInnings: (stateData.total_innings as number) || 9,
    activePitcherId: stateData.active_pitcher as string | undefined,
    activeBatterId: stateData.active_batter as string | undefined,
    isGameOver: !!(stateData.is_game_over),
    winnerMessage: stateData.winner_message as string | undefined,
    rivalTeamName: stateData.rival_team_name as string | undefined,
    state_data: stateData,
    pitcher_strikeouts: payload.pitcher_strikeouts || {},
    batter_stats: payload.batter_stats || {},
    homeHits: payload.home_hits || 0, // ⭐ del backend
    awayHits: payload.away_hits || 0, // ⭐ del backend
    inning_runs: payload.inning_runs || {}, // ⭐ del backend: {"1_true": 2, "1_false": 1}
    active_pitcher: payload.active_pitcher, // ⭐ NUEVO: Datos completos del pitcher (incluyendo rarity)
    active_batter: payload.active_batter, // ⭐ NUEVO: Datos completos del bateador (incluyendo rarity)
  };
}

export const useStadiumSocket = (
  gameId: string,
  userId: string,
  callbacks?: WebSocketCallbacks
): UseStadiumSocketReturn => {
  const [gameState, setGameState] = useState<GameStateWS | null>(null);
  const [hasPitched, setHasPitched] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId || !userId) return;

    const wsHost = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
      .replace(/^http/, 'ws');
    const wsUrl = `${wsHost}/ws/games/${gameId}/${userId}`;

    // Flag para ignorar eventos si el efecto ya fue limpiado (doble montaje de StrictMode)
    let cancelled = false;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      if (cancelled) { ws.close(); return; }
      setIsConnected(true);
      console.log(`[WS] Conectado exitosamente a ${gameId}`);
    };

    ws.onmessage = (event) => {
      if (cancelled) return;
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'INIT_GAME_STATE': {
            const payload = data as InitGameStatePayload;
            setGameState(parseStateData(payload));
            callbacks?.onGameStateInit?.(payload);
            break;
          }

          case 'PITCH_COMMITTED': {
            const payload = data as PitchCommittedPayload;
            // PITCH_COMMITTED es inmediato, no pasa por sequencer
            setHasPitched(payload.has_pitched);
            break;
          }

          case 'PLAY_RESOLVED': {
            const payload = data as PlayResolvedPayload;
            console.log('🔵 [FRONTEND] PLAY_RESOLVED received:');
            console.log('   event:', payload.event);
            console.log('   score_home:', payload.score_home);
            console.log('   score_away:', payload.score_away);
            
            // ⭐ Fase 1 Change: No actualizar state aquí
            // Simplemente notificar al parent para que enquee el evento
            callbacks?.onPlayResolved?.(payload);
            
            break;
          }

          case 'STEAL_RESOLVED': {
            // STEAL_RESOLVED se trata como un tipo de PLAY_RESOLVED
            const payload = data;
            console.log('🔄 [WS] STEAL_RESOLVED received:', payload);
            callbacks?.onPlayResolved?.(payload);
            break;
          }

          case 'PITCHER_CHANGED': {
            console.log('🔄 [WS] PITCHER_CHANGED recibido:', data);
            // ⭐ Fase 1 Change: No actualizar state aquí
            // Notificar al parent para que enquee el evento
            callbacks?.onPitcherChanged?.(data);
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
      if (cancelled) return;
      setIsConnected(false);
      console.log(`[WS] Desconectado de la partida ${gameId}`);
    };

    ws.onerror = (err) => {
      if (cancelled) return;
      console.error('[WS] Error de conexión:', err);
      console.error('[WS] URL intentada:', wsUrl);
    };

    return () => {
      // Marcar como cancelado para ignorar cualquier evento pendiente
      cancelled = true;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [gameId, userId, callbacks]);

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

  return { gameState, hasPitched, isConnected, sendPitch, sendSwing, sendTactic };
};