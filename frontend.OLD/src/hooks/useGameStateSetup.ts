import { useEffect } from 'react';

/**
 * Hook para inicializar y mantener los datos de los lineups
 * Descarga los datos de los jugadores basado en state_data del gameState
 */
export const useGameStateSetup = (
  gameState: any,
  userRole: 'HOME' | 'AWAY',
  cardsApi: any,
  setUserLineupCards: (cards: any[]) => void,
  setCpuLineupCards: (cards: any[]) => void,
  userTeam: any,
  gameState_rivalTeamName: string | undefined,
) => {
  useEffect(() => {
    if (!gameState?.state_data) return;

    const state = gameState.state_data as any;

    // Buscar lineups en diferentes posibles ubicaciones
    let userLineupIds = state.user_lineup_ids || state.userLineupIds || [];
    let cpuLineupIds = state.cpu_lineup_ids || state.cpuLineupIds || [];

    // Si aún están vacíos y hay datos de home/away, usar esos
    if (userLineupIds.length === 0) {
      userLineupIds = userRole === 'HOME' ? (state.home_lineup || []) : (state.away_lineup || []);
    }
    if (cpuLineupIds.length === 0) {
      cpuLineupIds = userRole === 'HOME' ? (state.away_lineup || []) : (state.home_lineup || []);
    }

    // Si los lineups están vacíos después de todo, no cargar nada
    if (userLineupIds.length === 0) {
      setUserLineupCards([]);
      setCpuLineupCards([]);
      return;
    }

    // Load user lineup en paralelo
    const userPromises = userLineupIds.map((cardId: string) =>
      cardsApi.getCard(cardId)
        .then((c: any) => ({
          id: c.id,
          name: c.name,
          number: c.number || '0',
          photo: c.photo,
          overall: c.overall || 0,
          position: c?.position || 'DH',
        }))
        .catch(() => ({ 
          id: cardId, 
          name: 'Unknown', 
          number: '?', 
          photo: undefined, 
          overall: 0, 
          position: 'DH' 
        }))
    );

    // Load CPU lineup en paralelo
    const cpuPromises = cpuLineupIds.map((cardId: string) =>
      cardsApi.getCard(cardId)
        .then((c: any) => ({
          id: c.id,
          name: c.name,
          number: c.number || '0',
          photo: c.photo,
          overall: c.overall || 0,
          position: c?.position || 'DH',
        }))
        .catch(() => ({ 
          id: cardId, 
          name: 'Unknown', 
          number: '?', 
          photo: undefined, 
          overall: 0, 
          position: 'DH' 
        }))
    );

    // Esperar a que ambos se completen
    Promise.all(userPromises).then(setUserLineupCards);
    Promise.all(cpuPromises).then(setCpuLineupCards);
  }, [gameState?.state_data, userRole, cardsApi]);
};
