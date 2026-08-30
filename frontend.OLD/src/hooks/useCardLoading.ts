import { useEffect, useState } from 'react';

/**
 * Hook para cargar datos de pitcher y batter
 * Prioriza WebSocket data, fallback a API
 */
export const useCardLoading = (
  gameState: any,
  userRole: 'HOME' | 'AWAY',
  userTeam: any,
  userLineupCards: any[],
  cardsApi: any,
) => {
  const [pitcherCard, setPitcherCard] = useState<any>(null);
  const [cpuPitcherCard, setCpuPitcherCard] = useState<any>(null);
  const [batterCard, setBatterCard] = useState<any>(null);

  // Pitcher effect - carga el pitcher del usuario
  useEffect(() => {
    if (!gameState) return;
    
    if (gameState.active_pitcher) {
      setPitcherCard(gameState.active_pitcher);
      console.log('✅ Pitcher from WebSocket:', { name: gameState.active_pitcher?.name, id: gameState.active_pitcher?.id });
      return;
    }

    // Durante intro, usar state_data. Durante juego, usar activePitcherId
    const pitcherId = gameState.activePitcherId || (userRole === 'HOME' ? gameState.state_data?.home_pitcher_id : gameState.state_data?.away_pitcher_id);
    
    console.log('🔴 User Pitcher Effect:', {
      activePitcherId: gameState.activePitcherId,
      userRole,
      pitcherId,
      home_pitcher_id: gameState.state_data?.home_pitcher_id,
      away_pitcher_id: gameState.state_data?.away_pitcher_id,
    });
    
    if (pitcherId) {
      cardsApi.getCard(pitcherId)
        .then((c: any) => {
          if (!c) return;
          
          const pitcherTeam = userTeam?.name;
          
          let bestVel = 75, bestControl = 70, bestMovement = 70;
          if (c.repertoire?.length > 0) {
            bestVel = Math.max(...c.repertoire.map((p: any) => p.velocity || 0));
            bestControl = Math.max(...c.repertoire.map((p: any) => p.control || 0));
            bestMovement = Math.max(...c.repertoire.map((p: any) => p.movement || 0));
          }
          
          console.log('✅ User Pitcher Loaded:', { name: c.name, id: c.id });
          
          setPitcherCard({
            id: c.id,
            name: c.name,
            number: c.number || '17',
            overall: c.overall || 99,
            position: c.position || 'SP',
            photo: c.photo,
            team: pitcherTeam || 'UNKNOWN',
            role: 'PITCHER',
            rarity: c.rarity || 'COMMON',
            repertoire: c.repertoire || [],
            stats: [
              { label: 'VEL', val: bestVel },
              { label: 'CTA', val: bestControl },
              { label: 'MCA', val: bestMovement },
            ]
          });
        })
        .catch((err) => {
          console.error('❌ Error loading user pitcher:', err);
        });
    }
  }, [gameState, userTeam, userRole, cardsApi]);

  // CPU Pitcher effect - carga el pitcher del CPU
  useEffect(() => {
    if (!gameState) return;
    
    // Siempre cargar el pitcher del CPU (opuesto al usuario)
    const cpuPitcherId = userRole === 'HOME' ? gameState.state_data?.away_pitcher_id : gameState.state_data?.home_pitcher_id;
    
    console.log('🔵 CPU Pitcher Effect:', {
      userRole,
      cpuPitcherId,
      home_pitcher_id: gameState.state_data?.home_pitcher_id,
      away_pitcher_id: gameState.state_data?.away_pitcher_id,
    });
    
    if (cpuPitcherId) {
      cardsApi.getCard(cpuPitcherId)
        .then((c: any) => {
          if (!c) return;
          
          const cpuTeam = gameState.rivalTeamName;
          
          let bestVel = 75, bestControl = 70, bestMovement = 70;
          if (c.repertoire?.length > 0) {
            bestVel = Math.max(...c.repertoire.map((p: any) => p.velocity || 0));
            bestControl = Math.max(...c.repertoire.map((p: any) => p.control || 0));
            bestMovement = Math.max(...c.repertoire.map((p: any) => p.movement || 0));
          }
          
          console.log('✅ CPU Pitcher Loaded:', { name: c.name, id: c.id, team_id: c.team_id });
          
          setCpuPitcherCard({
            id: c.id,
            name: c.name,
            number: c.number || '17',
            overall: c.overall || 99,
            position: c.position || 'SP',
            photo: c.photo,
            team: cpuTeam || 'UNKNOWN',
            team_id: c.team_id, // ⭐ NUEVO: Store team_id para cargar otros pitchers del mismo team
            role: 'PITCHER',
            rarity: c.rarity || 'COMMON',
            repertoire: c.repertoire || [],
            stats: [
              { label: 'VEL', val: bestVel },
              { label: 'CTA', val: bestControl },
              { label: 'MCA', val: bestMovement },
            ]
          });
        })
        .catch((err) => {
          console.error('❌ Error loading CPU Pitcher:', err);
        });
    }
  }, [gameState, userRole, cardsApi]);

  // Batter effect
  useEffect(() => {
    if (gameState?.active_batter) {
      setBatterCard(gameState.active_batter);
      return;
    }

    if (gameState?.activeBatterId) {
      cardsApi.getCard(gameState.activeBatterId)
        .then((c: any) => {
          if (!c) return;
          const isBatterUser = gameState.activeBatterId && userLineupCards.some(lc => lc.id === gameState.activeBatterId);
          const batterTeam = isBatterUser ? userTeam?.name : gameState?.rivalTeamName;
          const vision = Math.floor((c.contact || 50) * 0.70 + (c.overall || 75) * 0.30);
          
          setBatterCard({
            id: c.id,
            name: c.name,
            number: c.number || '17',
            overall: c.overall || 99,
            position: c.position || 'DH',
            photo: c.photo,
            team: batterTeam || 'UNKNOWN',
            role: 'BATTER',
            rarity: c.rarity || 'COMMON',
            stats: [
              { label: 'CON', val: c.contact || 50 },
              { label: 'POW', val: c.power || 50 },
              { label: 'VIS', val: vision },
            ]
          });
        })
        .catch(() => null);
    }
  }, [gameState?.active_batter, gameState?.activeBatterId, userTeam, gameState?.rivalTeamName, userLineupCards, cardsApi]);

  return { pitcherCard, cpuPitcherCard, batterCard, setPitcherCard, setCpuPitcherCard, setBatterCard };
};
