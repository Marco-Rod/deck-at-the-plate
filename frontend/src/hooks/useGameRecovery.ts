/**
 * useGameRecovery - Persiste y recupera sesión de gameplay
 * 
 * Propósito:
 * - Guardar gameId en localStorage cuando comienza una partida
 * - Recuperar gameId si se recarga la página durante gameplay
 * - Permitir continuar con la partida en lugar de perder el progreso
 * 
 * Uso:
 * - En App.jsx, llamar a useGameRecovery() para restaurar sesión
 * - Pasarlo a StadiumShowcaseScreen para guardar gameId
 * - Cuando se deja la partida, limpiar con clearGameSession()
 */

import { useEffect } from 'react';

const GAME_SESSION_KEY = 'deck_at_plate_active_game';

interface GameSessionData {
  gameId: string;
  userId: string;
  timestamp: number;
}

/**
 * Guardar sesión de juego en localStorage
 */
export const saveGameSession = (gameId: string, userId: string): void => {
  const session: GameSessionData = {
    gameId,
    userId,
    timestamp: Date.now(),
  };
  localStorage.setItem(GAME_SESSION_KEY, JSON.stringify(session));
  console.log('💾 [GameRecovery] Sesión guardada:', { gameId, userId });
};

/**
 * Recuperar sesión de juego desde localStorage
 */
export const getGameSession = (): GameSessionData | null => {
  try {
    const stored = localStorage.getItem(GAME_SESSION_KEY);
    if (!stored) return null;
    
    const session = JSON.parse(stored) as GameSessionData;
    console.log('📂 [GameRecovery] Sesión recuperada:', session);
    return session;
  } catch (error) {
    console.error('❌ [GameRecovery] Error al recuperar sesión:', error);
    return null;
  }
};

/**
 * Limpiar sesión de juego (al salir o terminar partida)
 */
export const clearGameSession = (): void => {
  localStorage.removeItem(GAME_SESSION_KEY);
  console.log('🗑️ [GameRecovery] Sesión limpiada');
};

/**
 * Hook para gestionar recuperación de sesión
 * 
 * @param onSessionRecovered - Callback cuando se recupera una sesión (gameId, userId)
 */
export const useGameRecovery = (
  onSessionRecovered?: (gameId: string, userId: string) => void
): void => {
  useEffect(() => {
    const session = getGameSession();
    if (session && onSessionRecovered) {
      // Validar que la sesión no sea demasiado antigua (opcional: máx 1 hora)
      const ageMs = Date.now() - session.timestamp;
      const maxAgeMs = 60 * 60 * 1000; // 1 hora
      
      if (ageMs < maxAgeMs) {
        console.log('✅ [GameRecovery] Recuperando sesión activa');
        onSessionRecovered(session.gameId, session.userId);
      } else {
        console.log('⏰ [GameRecovery] Sesión expirada (más de 1 hora)');
        clearGameSession();
      }
    }
  }, [onSessionRecovered]);
};
