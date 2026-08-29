/**
 * useGameStatePersistence — Hook para persistir y recuperar el estado del juego en localStorage
 * ============================================================================================
 * 
 * Problemas resueltos:
 * - Si la página se recarga, se pierde todo el estado del juego
 * - Datos como pitcher_strikeouts, pitch counts, fatigue no se guardaban
 * - No había forma de recuperarse de caídas de conexión
 * 
 * Características:
 * - Guarda automáticamente cada cambio en gameState
 * - Recupera el estado anterior al recargar
 * - Limpia localStorage cuando el juego termina
 * - Detecta datos faltantes y los valida
 */

import { useEffect } from 'react';
import { GameStateWS } from '../types/stadium';

const GAME_STATE_KEY = 'game_state_persistence';
const GAME_METADATA_KEY = 'game_metadata';

interface GameMetadata {
  gameId: string;
  userId: string;
  savedAt: number;
  lastInning: number;
}

/**
 * Guarda el estado del juego en localStorage
 */
export const persistGameState = (gameState: GameStateWS | null, gameId: string, userId: string) => {
  if (!gameState) return;

  try {
    // Validar que tenemos los datos críticos
    const dataToSave = {
      // Datos básicos del juego
      currentInning: gameState.currentInning,
      isTopInning: gameState.isTopInning,
      homeScore: gameState.homeScore,
      awayScore: gameState.awayScore,
      balls: gameState.balls,
      strikes: gameState.strikes,
      outs: gameState.outs,
      
      // Runners
      runners: gameState.runners,
      
      // IDs de jugadores activos
      activePitcherId: gameState.activePitcherId,
      activeBatterId: gameState.activeBatterId,
      
      // Estado del juego
      isGameOver: gameState.isGameOver,
      winnerMessage: gameState.winnerMessage,
      rivalTeamName: gameState.rivalTeamName,
      userRole: gameState.userRole,
      
      // ⭐ CRITICAL: Estadísticas del pitcher
      pitcher_strikeouts: gameState.pitcher_strikeouts || {},
      batter_stats: gameState.batter_stats || {},
      
      // Otros datos
      homeHits: gameState.homeHits,
      awayHits: gameState.awayHits,
      inning_runs: gameState.inning_runs || {},
      
      // state_data completo (contiene info del backend)
      state_data: gameState.state_data || {},
    };

    // Guardar estado del juego
    localStorage.setItem(GAME_STATE_KEY, JSON.stringify(dataToSave));

    // Guardar metadata
    const metadata: GameMetadata = {
      gameId,
      userId,
      savedAt: Date.now(),
      lastInning: gameState.currentInning,
    };
    localStorage.setItem(GAME_METADATA_KEY, JSON.stringify(metadata));

    console.log('💾 [PERSISTENCE] gameState guardado en localStorage:', {
      inning: gameState.currentInning,
      scores: { home: gameState.homeScore, away: gameState.awayScore },
      pitcher_strikeouts_count: Object.keys(gameState.pitcher_strikeouts || {}).length,
      savedAt: new Date().toLocaleTimeString(),
    });
  } catch (err) {
    console.error('❌ [PERSISTENCE] Error guardando gameState:', err);
  }
};

/**
 * Recupera el estado del juego desde localStorage
 */
export const recoverGameState = (gameId: string, userId: string): GameStateWS | null => {
  try {
    // Verificar que sea el mismo juego y usuario
    const metadataStr = localStorage.getItem(GAME_METADATA_KEY);
    if (!metadataStr) {
      console.log('ℹ️  [PERSISTENCE] No hay estado previo guardado');
      return null;
    }

    const metadata: GameMetadata = JSON.parse(metadataStr);
    if (metadata.gameId !== gameId || metadata.userId !== userId) {
      console.log('ℹ️  [PERSISTENCE] Estado previo es de otro juego, ignorando');
      clearPersistedGameState();
      return null;
    }

    const gameStateStr = localStorage.getItem(GAME_STATE_KEY);
    if (!gameStateStr) return null;

    const savedState = JSON.parse(gameStateStr);
    
    // Reconstruir GameStateWS
    const recovered: GameStateWS = {
      currentInning: savedState.currentInning,
      isTopInning: savedState.isTopInning,
      homeScore: savedState.homeScore,
      awayScore: savedState.awayScore,
      balls: savedState.balls,
      strikes: savedState.strikes,
      outs: savedState.outs,
      runners: savedState.runners,
      totalInnings: savedState.state_data?.total_innings || 9,
      activePitcherId: savedState.activePitcherId,
      activeBatterId: savedState.activeBatterId,
      isGameOver: savedState.isGameOver,
      winnerMessage: savedState.winnerMessage,
      rivalTeamName: savedState.rivalTeamName,
      userRole: savedState.userRole || 'HOME',
      state_data: savedState.state_data,
      pitcher_strikeouts: savedState.pitcher_strikeouts || {},
      batter_stats: savedState.batter_stats || {},
      homeHits: savedState.homeHits || 0,
      awayHits: savedState.awayHits || 0,
      inning_runs: savedState.inning_runs || {},
      active_pitcher: undefined,
      active_batter: undefined,
      inning_completed: undefined,
    };

    console.log('✅ [PERSISTENCE] gameState recuperado de localStorage:', {
      inning: recovered.currentInning,
      scores: { home: recovered.homeScore, away: recovered.awayScore },
      pitcher_strikeouts_count: Object.keys(recovered.pitcher_strikeouts || {}).length,
      recoveredAt: new Date().toLocaleTimeString(),
    });

    return recovered;
  } catch (err) {
    console.error('❌ [PERSISTENCE] Error recuperando gameState:', err);
    clearPersistedGameState();
    return null;
  }
};

/**
 * Limpia el estado guardado (cuando el juego termina)
 */
export const clearPersistedGameState = () => {
  try {
    localStorage.removeItem(GAME_STATE_KEY);
    localStorage.removeItem(GAME_METADATA_KEY);
    console.log('🧹 [PERSISTENCE] Estado del juego limpiado de localStorage');
  } catch (err) {
    console.error('❌ [PERSISTENCE] Error limpiando gameState:', err);
  }
};

/**
 * Hook para usar la persistencia en un componente
 * Ejemplo:
 * 
 * const recoveredState = useGameStatePersistence(gameState, gameId, userId);
 * 
 * if (gameState && recoveredState && !wasRecovered) {
 *   // El primer gameState vino de la persistencia
 * }
 */
export const useGameStatePersistence = (
  gameState: any,
  gameId: string,
  userId: string,
  enabled = true
) => {
  useEffect(() => {
    if (!enabled || !gameState || !gameId || !userId) return;

    // Si el juego terminó, limpiar persistencia
    if (gameState.isGameOver) {
      clearPersistedGameState();
      return;
    }

    // Guardar en localStorage cada vez que gameState cambie
    persistGameState(gameState, gameId, userId);
  }, [gameState, gameId, userId, enabled]);
};

/**
 * Valida la integridad de los datos guardados
 */
export const validatePersistedGameState = (gameId: string, userId: string): boolean => {
  try {
    const metadataStr = localStorage.getItem(GAME_METADATA_KEY);
    const gameStateStr = localStorage.getItem(GAME_STATE_KEY);

    if (!metadataStr || !gameStateStr) return false;

    const metadata: GameMetadata = JSON.parse(metadataStr);
    const gameState = JSON.parse(gameStateStr);

    // Validaciones básicas
    const isValid =
      metadata.gameId === gameId &&
      metadata.userId === userId &&
      typeof gameState.currentInning === 'number' &&
      typeof gameState.homeScore === 'number' &&
      typeof gameState.awayScore === 'number' &&
      gameState.pitcher_strikeouts !== undefined;

    if (isValid) {
      console.log('✅ [PERSISTENCE] Datos guardados validados correctamente');
    } else {
      console.warn('⚠️  [PERSISTENCE] Datos guardados inválidos o incompletos');
    }

    return isValid;
  } catch (err) {
    console.error('❌ [PERSISTENCE] Error validando datos:', err);
    return false;
  }
};

/**
 * Obtiene información sobre el estado guardado (para debugging)
 */
export const getPersistedGameStateInfo = () => {
  try {
    const metadataStr = localStorage.getItem(GAME_METADATA_KEY);
    const gameStateStr = localStorage.getItem(GAME_STATE_KEY);

    if (!metadataStr || !gameStateStr) {
      return { saved: false };
    }

    const metadata: GameMetadata = JSON.parse(metadataStr);
    const gameState = JSON.parse(gameStateStr);

    const timeSinceSave = Date.now() - metadata.savedAt;
    const minutesSinceSave = Math.round(timeSinceSave / 60000);

    return {
      saved: true,
      gameId: metadata.gameId,
      lastInning: metadata.lastInning,
      scores: {
        home: gameState.homeScore,
        away: gameState.awayScore,
      },
      minutesSinceSave,
      pitchersWithStrikeouts: Object.keys(gameState.pitcher_strikeouts || {}).length,
    };
  } catch (err) {
    console.error('❌ [PERSISTENCE] Error obteniendo info:', err);
    return { saved: false, error: String(err) };
  }
};
