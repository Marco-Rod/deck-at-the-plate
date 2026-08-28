import React, { useState, useEffect, useRef } from 'react';
// Barrel imports from refactored stadium module
import {
  GameHeader,
  Scoreboard,
  GameInfo,
  PitchZoneGrid,
  GameStatsPanel,
  TacticalHand,
  CentralField,
  PitcherStaminaBar,
} from './index';
import { PlayerCard } from './PlayerCard';
import { PlayResultOverlay } from './PlayResultOverlay';
import { GameOverModal } from './GameOverModal';
import { InningTransitionModal } from './InningTransitionModal';
import { GameIntroModal } from './GameIntroModal';
import { GameplayDeckAndReveal } from './GameplayDeckAndReveal';
import { QuitGameModal } from './QuitGameModal';
import { useStadiumSocket } from '../../hooks/useStadiumSocket';
import { games as gamesApi, cards as cardsApi, user as userApi } from '../../utils/api';

import type {
  PitchType,
  PlayerData,
  PlayerRole,
  TacticalCard,
} from '../../types/stadium';

interface StadiumShowcaseScreenProps {
  gameId: string | null;
  userId: string;
  onBack: () => void;
}

export const StadiumShowcaseScreen: React.FC<StadiumShowcaseScreenProps> = ({
  gameId,
  userId,
  onBack,
}) => {
  const [selectedZone, setSelectedZone] = useState<number>(5);
  const [selectedPitch, setSelectedPitch] = useState<PitchType>('4-SEAM');
  const [selectedSwing, setSelectedSwing] = useState<'NORMAL' | 'POWER' | 'TAKE' | 'BUNT'>('NORMAL');
  const [selectedTacticalId, setSelectedTacticalId] = useState<string | null>(null);

  // Bloquea los controles desde que se envía la jugada hasta 1 seg después de recibir el resultado
  const [isAwaitingResult, setIsAwaitingResult] = useState(false);
  // Retrasa el GameOverModal para que el PlayResultOverlay del evento final
  // (home run, strikeout, etc.) tenga tiempo de mostrarse antes del resumen.
  const [showGameOverModal, setShowGameOverModal] = useState(false);
  // Estado del modal de transición de inning: visible, inning completado, siguiente inning
  const [inningTransition, setInningTransition] = useState<{
    visible: boolean;
    completedInning: number;
    completedHalf: 'TOP' | 'BOT';
    nextInning: number;
    nextHalf: 'TOP' | 'BOT';
  } | null>(null);
  
  // ⭐ NUEVO: Control del modal intro del juego
  const [showGameIntro, setShowGameIntro] = useState(true);

  const [pitcherCard, setPitcherCard] = useState<PlayerData | null>(null);
  const [batterCard, setBatterCard] = useState<PlayerData | null>(null);
  const [userTeam, setUserTeam] = useState<any>(null);
  
  // ⭐ NUEVO: Estados para el modal intro
  const [userLineupCards, setUserLineupCards] = useState<{ id?: string; name: string; number: string; photo?: string; overall?: number; position?: string }[]>([]);
  const [cpuPitcherCard, setCpuPitcherCard] = useState<{ name: string; number: string; photo?: string; overall?: number; position?: string } | null>(null);
  const [cpuLineupCards, setCpuLineupCards] = useState<{ id?: string; name: string; number: string; photo?: string; overall?: number; position?: string }[]>([]);
  
  // ⭐ NUEVO: Estados para estadísticas en tiempo real
  const [gameStats, setGameStats] = useState<Record<string, any>>({});
  const [strikeoutAnimationTrigger, setStrikeoutAnimationTrigger] = useState(false);
  
  // ⭐ NUEVO: Estados para el modal de finalizar partido
  const [showQuitModal, setShowQuitModal] = useState(false);
  const [isQuittingGame, setIsQuittingGame] = useState(false);
  
  const lastProcessedInningCompletedRef = useRef<number | null>(null);

  const { gameState, lastResult, inningCompleted, hasPitched, isConnected, pitcherChanged, sendPitch, sendSwing, sendTactic } =
    useStadiumSocket(gameId ?? '', userId);

  // ⭐ NUEVO: Calcular strikeouts del pitcher activo desde WebSocket
  const getPitcherStrikeouts = () => {
    const activePitcherId = gameState?.activePitcherId;
    
    // No tenemos pitcher activo
    if (!activePitcherId) {
      return 0;
    }
    
    // Obtener strikeouts del pitcher activo
    const pitchers = gameStats.pitchers || {};
    const so = pitchers[activePitcherId] ?? 0;
    
    console.log('✅ [SO COUNTER]', {
      activePitcherId,
      strikeouts: so,
      availablePitchers: Object.keys(pitchers),
    });
    
    return so;
  };

  // ⭐ NUEVO: Determinar pitcher ganador y sus SO basado en el winner
  const getWinningPitcherInfo = () => {
    if (!gameState?.isGameOver) return { name: undefined, strikeouts: 0 };
    
    // Determinar quién ganó (user o CPU)
    const userTeamScore = userRole === 'HOME' ? gameState.homeScore : gameState.awayScore;
    const cpuTeamScore = userRole === 'HOME' ? gameState.awayScore : gameState.homeScore;
    
    const userWon = userTeamScore > cpuTeamScore;
    
    // ⭐ CORRECCIÓN: El pitcher ganador es el del EQUIPO QUE GANÓ, no solo el activePitcherId
    let winningPitcherId: string | undefined;
    
    if (userWon) {
      // Usuario ganó → su pitcher es el ganador
      winningPitcherId = userRole === 'HOME' 
        ? gameState.state_data?.home_pitcher_id 
        : gameState.state_data?.away_pitcher_id;
    } else {
      // CPU ganó → su pitcher es el ganador
      winningPitcherId = userRole === 'HOME' 
        ? gameState.state_data?.away_pitcher_id 
        : gameState.state_data?.home_pitcher_id;
    }
    
    if (!winningPitcherId) {
      return { name: undefined, strikeouts: 0 };
    }
    
    // Obtener SO del pitcher ganador
    const pitchers = gameStats.pitchers || {};
    const winningPitcherSO = pitchers[winningPitcherId] ?? 0;
    
    // Determinar nombre del pitcher ganador
    let winningPitcherName = "Pitcher";
    
    if (userWon) {
      // Usuario ganó: su pitcher
      if (pitcherCard?.id === winningPitcherId) {
        winningPitcherName = pitcherCard.name || "Pitcher";
      }
    } else {
      // CPU ganó: pitcher del CPU
      if (cpuPitcherCard?.id === winningPitcherId) {
        winningPitcherName = cpuPitcherCard.name || "Pitcher";
      }
    }
    
    console.log('🏆 [WINNING PITCHER]', {
      name: winningPitcherName,
      strikeouts: winningPitcherSO,
      userWon,
      winningPitcherId,
      userRole,
    });
    
    return {
      name: winningPitcherName,
      strikeouts: winningPitcherSO,
    };
  };

  // ⭐ NUEVO: Obtener nombre del pitcher activo dinámicamente
  const getActivePitcherName = () => {
    if (!gameState?.activePitcherId) return "Pitcher";
    
    // Si es el pitcher del usuario (almacenado en pitcherCard)
    if (pitcherCard?.id === gameState.activePitcherId) {
      return pitcherCard.name || "Pitcher";
    }
    
    // Si es el pitcher del CPU (almacenado en cpuPitcherCard)
    if (cpuPitcherCard?.name) {
      return cpuPitcherCard.name;
    }
    
    return "Pitcher";
  };

  // lastResult ya viene como {text, ts} desde el hook — cada jugada es un objeto nuevo,
  // así que este useEffect siempre dispara aunque el texto sea idéntico al anterior.
  useEffect(() => {
    if (lastResult) {
      const timer = setTimeout(() => {
        setIsAwaitingResult(false);
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [lastResult, gameId]);

  // ⭐ NUEVO: Actualizar gameStats desde WebSocket payload
  useEffect(() => {
    if (gameState) {
      const pitchers = gameState.pitcher_strikeouts || {};
      const batters = gameState.batter_stats || {};
      
      // ⭐ MEJORADO: Logging más detallado de batter_stats
      console.log('📊 [UPDATED STATS FROM WEBSOCKET]:', {
        pitchers: Object.keys(pitchers).length > 0 ? pitchers : 'empty',
        batters: Object.keys(batters).length,
        batter_stats_full: batters, // Mostrar datos completos
        batter_sample: Object.entries(batters).slice(0, 1).map(([id, stats]) => ({
          batter_id: id,
          ab: (stats as any).at_bats,
          h: (stats as any).hits,
          hr: (stats as any).home_runs,
          bb: (stats as any).walks,
          rbi: (stats as any).rbi,
          r: (stats as any).runs,
          so: (stats as any).strikeouts,
        })),
      });
      
      setGameStats({
        pitchers,
        batters,
      });
      
      // Trigger animation si hay strikeouts
      const activePitcherId = gameState.activePitcherId;
      if (activePitcherId && pitchers[activePitcherId] > 0) {
        setStrikeoutAnimationTrigger(true);
        const timer = setTimeout(() => setStrikeoutAnimationTrigger(false), 500);
        return () => clearTimeout(timer);
      }
    }
  }, [gameState?.pitcher_strikeouts, gameState?.activePitcherId, gameState?.batter_stats]);

  // Detecta cuando la entrada termina (backend envía inning_completed=true)
  // y muestra el modal de transición con timing correcto.
  useEffect(() => {
    if (!inningCompleted || !gameState) return;

    // Evitar procesar el mismo inningCompleted dos veces usando ref
    if (lastProcessedInningCompletedRef.current === inningCompleted.ts) {
      return;
    }

    lastProcessedInningCompletedRef.current = inningCompleted.ts;

    // ⭐ NUEVO: Si el juego ya terminó, NO mostrar el modal de transición de entrada
    if (gameState?.isGameOver) {
      console.log('🎮 [INNING_TRANSITION] Omitiendo modal: el juego ha terminado');
      return;
    }

    // EVENT_DURATIONS: cuánto tarda el overlay en mostrarse (delayMs + duration)
    const EVENT_DURATIONS: Record<string, number> = {
      HOME_RUN:       1000 + 3500,
      HIT_3B:         1000 + 3000,
      HIT_2B:         1000 + 2800,
      HIT_1B:         1000 + 2500,
      STRIKEOUT:      1000 + 2800,
      OUT_FLY:        1000 + 2500,
      OUT_GROUND:     1000 + 2500,
      WALK:           1000 + 2500,
    };
    const eventKey = lastResult?.event?.toUpperCase() ?? '';
    const overlayDuration = EVENT_DURATIONS[eventKey] ?? 1000 + 2500;

    // Calcular qué inning/half acaba de completarse.
    // Cuando llega inning_completed, el estado ya fue actualizado, así que:
    // - Si ahora es TOP, entonces acaba de completarse BOT del inning anterior
    // - Si ahora es BOT, entonces acaba de completarse TOP del mismo inning
    const completedInning = gameState.isTopInning 
      ? gameState.currentInning - 1 
      : gameState.currentInning;
    const completedHalf = gameState.isTopInning ? 'BOT' : 'TOP';
    const nextInning = gameState.currentInning;
    const nextHalf = gameState.isTopInning ? 'TOP' : 'BOT';

    // Espera a que el overlay termine y luego muestra el modal
    const timer = setTimeout(() => {
      setInningTransition({
        visible: true,
        completedInning,
        completedHalf,
        nextInning,
        nextHalf,
      });
    }, overlayDuration);

    return () => clearTimeout(timer);
  }, [inningCompleted?.ts, gameState, lastResult]);

  // Cuando el juego termina, esperar a que el PlayResultOverlay del evento final
  // (home run = 1000ms delay + 3500ms duración = ~4.5s) haya terminado antes
  // de mostrar el GameOverModal. Se usa el event del lastResult para ajustar
  // el delay según el tipo de jugada final.
  useEffect(() => {
    if (!gameState?.isGameOver) return;

    // Calcular cuánto tarda el overlay del evento final en mostrarse y desaparecer
    const EVENT_DURATIONS: Record<string, number> = {
      HOME_RUN:       1000 + 3500, // delayMs + duration del tema HOME_RUN
      HIT_3B:         1000 + 3000,
      HIT_2B:         1000 + 2800,
      HIT_1B:         1000 + 2500,
      STRIKEOUT:      1000 + 2800,
      OUT_FLY:        1000 + 2500,
      OUT_GROUND:     1000 + 2500,
      WALK:           1000 + 2500,
    };
    const eventKey = lastResult?.event?.toUpperCase() ?? '';
    const overlayDuration = EVENT_DURATIONS[eventKey] ?? 1000 + 2500;

    const timer = setTimeout(() => {
      setShowGameOverModal(true);
    }, overlayDuration);

    return () => clearTimeout(timer);
  }, [gameState?.isGameOver]);

  // ⭐ ARREGLADO: Determinar el rol basado en gameState.state_data.user_role
  // user_role viene del backend (HOME o AWAY)
  // - Si usuario es HOME: pichea en Alta, batea en Baja
  // - Si usuario es AWAY: batea en Alta, pichea en Baja
  const userRole = gameState?.state_data?.user_role as "HOME" | "AWAY" | undefined;
  const role: PlayerRole = !gameState 
    ? 'BATTER'
    : (() => {
        if (userRole === 'HOME') {
          // Usuario es local: pichea en Alta, batea en Baja
          return gameState.isTopInning ? 'PITCHER' : 'BATTER';
        } else {
          // Usuario es visitante (AWAY): batea en Alta, pichea en Baja
          return gameState.isTopInning ? 'BATTER' : 'PITCHER';
        }
      })();

  // ⭐ NUEVO: Determinar lineup a mostrar: quien va a batear
  const getBattingLineup = () => {
    if (!gameState) return [];
    
    // Si usuario es HOME:
    //   - TOP (isTopInning=true): usuario pichea, CPU batea → mostrar cpuLineupCards
    //   - BOT (isTopInning=false): usuario batea, CPU pichea → mostrar userLineupCards
    // Si usuario es AWAY:
    //   - TOP (isTopInning=true): usuario batea, CPU pichea → mostrar userLineupCards
    //   - BOT (isTopInning=false): usuario pichea, CPU batea → mostrar cpuLineupCards
    
    const isBattingUser = 
      (userRole === 'HOME' && !gameState.isTopInning) ||
      (userRole === 'AWAY' && gameState.isTopInning);
    
    return isBattingUser ? userLineupCards : cpuLineupCards;
  };

  // ⭐ NUEVO: Determinar etiqueta del panel izquierdo (siempre lineup del bateador)
  const getBattingLineupLabel = () => {
    if (!gameState) return 'LINEUP';
    
    const isBattingUser = 
      (userRole === 'HOME' && !gameState.isTopInning) ||
      (userRole === 'AWAY' && gameState.isTopInning);
    
    return isBattingUser ? 'YOUR LINEUP' : 'CPU LINEUP';
  };

  useEffect(() => {
    if (!gameState?.state_data) return;

    const state = gameState.state_data as any;
    
    // Cargar lineup del usuario
    if (state.home_lineup || state.away_lineup) {
      const userLineupIds = userRole === 'HOME' ? state.home_lineup : state.away_lineup;
      if (userLineupIds && userLineupIds.length > 0) {
        Promise.all(
          userLineupIds.slice(0, 9).map((cardId: string) =>
            cardsApi.getCard(cardId)
              .then((c: any) => ({
                id: cardId,  // ⭐ NUEVO: guardar el ID para lookup de stats
                name: c?.name || 'Unknown',
                number: c?.number || '?',
                photo: c?.photo,
                overall: c?.overall || 0,
                position: c?.position || 'DH',
              }))
              .catch(() => ({ id: cardId, name: 'Unknown', number: '?', photo: undefined, overall: 0, position: 'DH' }))
          )
        ).then(setUserLineupCards);
      }
    }

    // Cargar pitcher CPU
    const cpuPitcherId = userRole === 'HOME' ? state.away_pitcher_id : state.home_pitcher_id;
    if (cpuPitcherId) {
      cardsApi.getCard(cpuPitcherId)
        .then((c: any) => {
          setCpuPitcherCard({
            name: c?.name || 'Unknown',
            number: c?.number || '?',
            photo: c?.photo,
            overall: c?.overall || 0,
            position: c?.position || 'SP',
          });
        })
        .catch(() => null);
    }

    // Cargar lineup CPU
    const cpuLineupIds = userRole === 'HOME' ? state.away_lineup : state.home_lineup;
    if (cpuLineupIds && cpuLineupIds.length > 0) {
      Promise.all(
        cpuLineupIds.slice(0, 9).map((cardId: string) =>
          cardsApi.getCard(cardId)
            .then((c: any) => ({
              id: cardId,  // ⭐ NUEVO: guardar el ID para lookup de stats
              name: c?.name || 'Unknown',
              number: c?.number || '?',
              photo: c?.photo,
              overall: c?.overall || 0,
              position: c?.position || 'DH',
            }))
            .catch(() => ({ id: cardId, name: 'Unknown', number: '?', photo: undefined, overall: 0, position: 'DH' }))
        )
      ).then(setCpuLineupCards);
    }
  }, [gameState?.state_data, userRole]);

  useEffect(() => {
    if (!userId) return;
    userApi.getTeam(userId).then(setUserTeam).catch(() => null);
  }, [userId]);

  useEffect(() => {
    // ⭐ PRIORIDAD: Si tenemos datos del pitcher desde el WebSocket (con rarity), usarlos directamente
    if (gameState?.active_pitcher) {
      setPitcherCard(gameState.active_pitcher);
      if (gameState.active_pitcher.repertoire && gameState.active_pitcher.repertoire.length > 0) {
        setSelectedPitch(gameState.active_pitcher.repertoire[0].pitch_type);
      }
      return;
    }

    // ⭐ FALLBACK: Si no, hacer fetch de la API (usado en primer carga si WebSocket llega después)
    if (gameState?.activePitcherId) {
      cardsApi.getCard(gameState.activePitcherId)
        .then((c: any) => {
          if (c) {
            // Determinar el equipo del pitcher
            const isPitcherUser = gameState.activePitcherId === gameState.state_data?.home_pitcher_id && userRole === 'HOME'
                               || gameState.activePitcherId === gameState.state_data?.away_pitcher_id && userRole === 'AWAY';
            const pitcherTeam = isPitcherUser ? userTeam?.name : gameState?.rivalTeamName;

            // Calcular stats del pitcher: VEL, CTA, MCA (mejores valores del repertorio)
            let bestVel = c.velocity || 75;
            let bestControl = c.control || 70;
            let bestMovement = c.movement || 70;
            
            if (c.repertoire && c.repertoire.length > 0) {
              const velocities = c.repertoire.map((p: any) => p.velocity || 0);
              const controls = c.repertoire.map((p: any) => p.control || 0);
              const movements = c.repertoire.map((p: any) => p.movement || 0);
              
              bestVel = Math.max(...velocities);
              bestControl = Math.max(...controls);
              bestMovement = Math.max(...movements);
            }

            setPitcherCard({
              id: c.id,
              name: c.name,
              number: c.number || '17',
              overall: c.overall || 99,
              position: c.position || 'SP',
              photo: c.photo,
              team: pitcherTeam || 'UNKNOWN',
              role: 'PITCHER',
              rarity: c.rarity || 'COMMON', // ⭐ NUEVO: Incluir rareza
              repertoire: c.repertoire || [],
              stats: [
                { label: 'VEL', val: bestVel },
                { label: 'CTA', val: bestControl },
                { label: 'MCA', val: bestMovement },
              ]
            });
            if (c.repertoire && c.repertoire.length > 0) {
              setSelectedPitch(c.repertoire[0].pitch_type);
            }
          }
        })
        .catch(() => null);
    }
  }, [gameState?.active_pitcher, gameState?.activePitcherId, userTeam, gameState?.rivalTeamName, userRole, gameState?.state_data]);

  useEffect(() => {
    // ⭐ PRIORIDAD: Si tenemos datos del bateador desde el WebSocket (con rarity), usarlos directamente
    if (gameState?.active_batter) {
      setBatterCard(gameState.active_batter);
      return;
    }

    // ⭐ FALLBACK: Si no, hacer fetch de la API (usado en primer carga si WebSocket llega después)
    if (gameState?.activeBatterId) {
      cardsApi.getCard(gameState.activeBatterId)
        .then((c: any) => {
          if (c) {
            // Determinar el equipo del bateador
            const isBatterUser = gameState.activeBatterId && userLineupCards.some(lc => lc.id === gameState.activeBatterId);
            const batterTeam = isBatterUser ? userTeam?.name : gameState?.rivalTeamName;

            // Calcular vision derivada como en el backend: contact * 0.70 + overall * 0.30
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
              rarity: c.rarity || 'COMMON', // ⭐ NUEVO: Incluir rareza
              stats: [
                { label: 'CON', val: c.contact || 50 },
                { label: 'POW', val: c.power || 50 },
                { label: 'VIS', val: vision },
              ]
            });
          }
        })
        .catch(() => null);
    }
  }, [gameState?.active_batter, gameState?.activeBatterId, userTeam, gameState?.rivalTeamName, userLineupCards]);

  // ── Reaccionar al cambio de pitcher vía WebSocket PITCHER_CHANGED ──────────
  // Cuando el backend confirma el cambio, actualizamos la carta, reseteamos
  // el pitch_count, la fatiga, y el selectedPitch al primer lanzamiento del nuevo pitcher.
  useEffect(() => {
    if (!pitcherChanged) return;

    const { newPitcher } = pitcherChanged;
    console.log('🔄 [PITCHER_CHANGED] Actualizando carta del pitcher:', newPitcher?.name);

    // 1. Actualizar la carta del pitcher con datos frescos del backend
    //    El backend ya envía: id, name, number, overall, position, rarity,
    //    stats, role, pitch_count: 0, fatigue_level: 0
    setPitcherCard({
      id: newPitcher.id,
      name: newPitcher.name,
      number: newPitcher.number,
      overall: newPitcher.overall,
      position: newPitcher.position,
      rarity: newPitcher.rarity || 'COMMON',
      team: newPitcher.team || '',
      role: 'PITCHER',
      photo: newPitcher.photo,
      repertoire: newPitcher.stats?.repertoire || newPitcher.repertoire || [],
      stats: newPitcher.stats || [],
      pitch_count: 0,
      fatigue_level: 0,
    });

    // 2. Resetear el tipo de pitch seleccionado al primero del repertorio nuevo
    const repertoire = newPitcher.repertoire || newPitcher.stats?.repertoire || [];
    if (repertoire.length > 0 && repertoire[0]?.pitch_type) {
      setSelectedPitch(repertoire[0].pitch_type);
    }

    // 3. Resetear animación de strikeouts para el nuevo pitcher
    setStrikeoutAnimationTrigger(false);

  }, [pitcherChanged?.ts]);

  // ── Fallback: si el gameState.active_pitcher cambió pero pitcherChanged aún no llegó ──
  // Esto asegura que el UI se sincronice incluso si el WS se retrasa
  useEffect(() => {
    if (!gameState?.active_pitcher) return;
    
    // Solo actualizar si es diferente del actual (evita loops)
    if (pitcherCard?.id !== gameState.active_pitcher.id) {
      console.log('🔄 [FALLBACK] Actualizando pitcher por gameState change:', gameState.active_pitcher.name);
      
      setPitcherCard({
        id: gameState.active_pitcher.id,
        name: gameState.active_pitcher.name,
        number: gameState.active_pitcher.number,
        overall: gameState.active_pitcher.overall,
        position: gameState.active_pitcher.position,
        rarity: gameState.active_pitcher.rarity || 'COMMON',
        team: gameState.active_pitcher.team || '',
        role: 'PITCHER',
        photo: gameState.active_pitcher.photo,
        repertoire: gameState.active_pitcher.repertoire || [],
        stats: gameState.active_pitcher.stats || [],
        pitch_count: gameState.active_pitcher.pitch_count ?? 0,
        fatigue_level: gameState.active_pitcher.fatigue_level ?? 0,
      });
      
      const rep = gameState.active_pitcher.repertoire || [];
      if (rep.length > 0 && rep[0]?.pitch_type) {
        setSelectedPitch(rep[0].pitch_type);
      }
    }
  }, [gameState?.active_pitcher?.id]);

  const tacticalHand: TacticalCard[] = [
    {
      id: 't1',
      name: 'RECTA FUEGO',
      cost: 1,
      desc: '+10 VEL en zona alta',
      type: 'PITCH BOOST',
      color: 'border-red-500/80 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]',
      icon: '🔥',
    },
    {
      id: 't2',
      name: 'PICONAZO',
      cost: 2,
      desc: 'Provoca Whiff fuera de zona',
      type: 'SPECIAL',
      color: 'border-[#C5A059] text-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)]',
      icon: '〰️',
    },
    {
      id: 't3',
      name: 'PITCHOUT',
      cost: 1,
      desc: 'Sorprende a corredor en robo',
      type: 'DEFENSE',
      color: 'border-blue-400/80 text-blue-300 shadow-[0_0_15px_rgba(96,165,250,0.3)]',
      icon: '🏃',
    },
    {
      id: 't4',
      name: 'TOQUE SUICIDA',
      cost: 2,
      desc: 'Asegura carrera desde 3B',
      type: 'OFFENSE',
      color: 'border-emerald-500/80 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]',
      icon: '🏏',
    },
  ];

  const handleSubmitPlay = async () => {
    if (isAwaitingResult || inningTransition?.visible) return;
    setIsAwaitingResult(true);
    try {
      if (role === 'PITCHER') {
        if (selectedTacticalId) {
          await sendTactic(selectedTacticalId, 'PITCHER');
          setSelectedTacticalId(null);
        }
        await sendPitch(selectedZone, selectedPitch);
      } else {
        if (selectedTacticalId) {
          await sendTactic(selectedTacticalId, 'BATTER');
          setSelectedTacticalId(null);
        }
        await sendSwing(selectedSwing, selectedZone, selectedPitch);
      }
    } catch {
      // Si falla la petición, desbloquear de inmediato para no dejar al usuario atascado
      setIsAwaitingResult(false);
    }
  };

  const handleQuitGame = async () => {
    setIsQuittingGame(true);
    try {
      // El WebSocket se cerrará automáticamente cuando onBack() desmonte el componente
      // Pequeño delay para asegurar que todo se sincronice
      await new Promise(resolve => setTimeout(resolve, 300));
      // Regresar al lobby - esto desmonta StadiumShowcaseScreen y cierra el WebSocket
      onBack();
    } catch (error) {
      console.error('Error al finalizar el partido:', error);
      setIsQuittingGame(false);
    }
  };

  // Cuando llega un resultado del backend, esperar 1 seg antes de liberar los controles.
  // Se usa un objeto {text, ts} en lugar de string plano para garantizar que el useEffect
  // siempre dispare, incluso cuando dos jugadas consecutivas producen el mismo texto
  // (ej. dos strikes seguidos, dos strikeouts, etc.).

  // Bloquea la interfaz mientras el modal de transición está visible (3s).
  // Se cierra el modal y se libera la interfaz después.
  // Una vez cerrado, reseteamos inningCompleted para evitar que dispare de nuevo.
  useEffect(() => {
    if (!inningTransition?.visible) return;

    const timer = setTimeout(() => {
      setInningTransition(null);
      // Resetear inningCompleted para que no dispare el modal nuevamente
      // Esto debe ocurrir DESPUÉS de que el modal se cierre completamente
    }, 3000);

    return () => clearTimeout(timer);
  }, [inningTransition?.visible]);

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-4 text-[#F7F5F0] relative overflow-hidden select-none">
      
      {/* MODAL INTRO DEL JUEGO — se muestra al entrar al partido */}
      {showGameIntro && gameState && (
        <GameIntroModal
          userTeamName={userTeam?.name || 'USUARIO'} // ⭐ ARREGLADO: usar name completo en lugar de short_name
          userTeamLogo={userTeam?.logo}
          userPitcher={pitcherCard ? {
            name: pitcherCard.name,
            number: pitcherCard.number,
            photo: pitcherCard.photo,
          } : undefined}
          userLineup={userLineupCards}
          cpuTeamName={gameState?.rivalTeamName ? `${gameState.rivalTeamName}` : 'CPU'} // ⭐ ARREGLADO: sin " (CPU)" redundante
          cpuTeamLogo={undefined}
          cpuPitcher={cpuPitcherCard}
          cpuLineup={cpuLineupCards}
          onPlayBall={() => setShowGameIntro(false)}
        />
      )}
      
      {/* MODAL DE FIN DE PARTIDO — se muestra tras el overlay del evento final */}
      {showGameOverModal && gameState?.isGameOver && (() => {
        const homeTeamDisplay = userRole === 'HOME' ? userTeam?.short_name : `${gameState?.rivalTeamName || 'YANKEES'} (CPU)`;
        const awayTeamDisplay = userRole === 'HOME' ? `${gameState?.rivalTeamName || 'YANKEES'} (CPU)` : userTeam?.short_name;
        const { name: winningPitcherName, strikeouts: winningPitcherSO } = getWinningPitcherInfo();
        return (
          <GameOverModal
            winnerMessage={gameState.winnerMessage}
            homeScore={gameState.homeScore}
            awayScore={gameState.awayScore}
            homeTeamName={homeTeamDisplay}
            awayTeamName={awayTeamDisplay}
            userRole={userRole}
            winningPitcherName={winningPitcherName}
            winningPitcherSO={winningPitcherSO}
            onReturnToLobby={onBack}
          />
        );
      })()}

      {/* MODAL DE TRANSICIÓN DE INNING — se muestra cuando termina una entrada */}
      {inningTransition?.visible && (
        <InningTransitionModal
          completedInning={inningTransition.completedInning}
          completedHalf={inningTransition.completedHalf}
          nextInning={inningTransition.nextInning}
          nextHalf={inningTransition.nextHalf}
          homeScore={gameState?.homeScore ?? 0}
          awayScore={gameState?.awayScore ?? 0}
          userRole={userRole} // ⭐ NUEVO: pasar userRole para intercambiar scores
        />
      )}

      {/* Header */}
      {!showGameIntro && (
      <header className="w-full flex justify-between items-center border-b-2 border-[#C5A059]/40 pb-3 mb-3 z-30">
        <div>
          <h2 className="font-sports text-3xl text-[#F7F5F0] uppercase tracking-wider leading-none">
            {userTeam ? `${userTeam.name} VS CPU` : 'CAMPO DE JUEGO'}
          </h2>
          <span className={`font-mono text-[10px] ${isConnected ? 'text-emerald-400' : 'text-red-400'}`}>
            {isConnected ? '● CONECTADO EN VIVO' : '○ DESCONECTADO'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowQuitModal(true)}
            className="bg-[#0A0D0F] border border-red-600 px-4 py-2 font-mono text-xs text-red-500 font-bold cursor-pointer hover:bg-red-600/10 transition-colors"
            title="Finalizar el partido actual"
          >
            🚪 FINALIZAR
          </button>
        </div>
      </header>
      )}

      {/* Marcador */}
      {!showGameIntro && gameState && (() => {
        const homeTeamDisplay = userRole === 'HOME' ? userTeam?.short_name : `${gameState?.rivalTeamName || 'YANKEES'} (CPU)`;
        const awayTeamDisplay = userRole === 'HOME' ? `${gameState?.rivalTeamName || 'YANKEES'} (CPU)` : userTeam?.short_name;
        
        // ⭐ DEBUG: Log antes de pasar al Scoreboard
        console.log('🎲 [STADIUM SHOWCASE] Pasando datos al Scoreboard:');
        console.log('  - gameState.inning_runs:', JSON.stringify(gameState?.inning_runs));
        console.log('  - gameState.homeScore:', gameState?.homeScore);
        console.log('  - gameState.awayScore:', gameState?.awayScore);
        
        return (
          <Scoreboard 
            gameState={gameState} 
            role={role}
            userRole={userRole}
            homeTeamName={homeTeamDisplay}
            awayTeamName={awayTeamDisplay}
            totalInnings={gameState?.totalInnings}
            homeHits={gameState?.homeHits || 0}
            awayHits={gameState?.awayHits || 0}
            inningRuns={gameState?.inning_runs || {}}
          />
        );
      })()}

      {/* Campo Principal */}
      {!showGameIntro && (
      <main 
        className="w-full sm:w-[95%] mx-auto border border-[#C5A059]/30 sm:border-2 sm:border-[#C5A059]/50 p-0.5 sm:p-1 md:p-2 relative flex flex-col md:flex-row justify-start md:justify-between items-start md:items-center min-h-auto md:min-h-[500px] shadow-2xl overflow-x-hidden md:overflow-hidden rounded-sm gap-1 md:gap-2 mt-0.5 sm:mt-1"
      >
        {/* Capa oscura translúcida */}
        <div className="absolute inset-0 bg-[#0A0D0F]/60 pointer-events-none" />

        {/* PANEL IZQUIERDO - Siempre el LINEUP del bateador (Responsive) */}
        <div className="relative z-10 w-full md:w-[450px] md:flex-shrink-0 order-1 md:order-1 overflow-y-auto max-h-[40vh] md:max-h-full">
          <div className="bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded p-1 sm:p-2 md:p-3 text-xs md:text-sm">
            <div className="text-[9px] sm:text-xs text-[#C5A059] font-bold mb-0.5 sm:mb-1 px-1 truncate">
              {getBattingLineupLabel()}
            </div>
            <GameStatsPanel
              lineup={getBattingLineup()}
              stats={gameStats?.batters || {}}
              isPitcher={false}
            />
          </div>
        </div>

        {/* CONTENEDOR CENTRAL - Campo de juego (Responsive) */}
        <div className="w-full md:flex-1 order-3 md:order-2 px-0.5 sm:px-1 md:px-2">
          <CentralField
            role={role}
            pitcherCard={pitcherCard}
            batterCard={batterCard}
            selectedZone={selectedZone}
            selectedPitch={selectedPitch}
            repertoire={pitcherCard?.repertoire}
            hasPitched={hasPitched}
            isAwaitingResult={isAwaitingResult}
            inningTransition={inningTransition}
            onSelectZone={setSelectedZone}
            onSelectPitch={setSelectedPitch}
            balls={gameState?.balls ?? 0}
            strikes={gameState?.strikes ?? 0}
            outs={gameState?.outs ?? 0}
            currentInning={gameState?.currentInning ?? 1}
            totalInnings={gameState?.totalInnings ?? 9}
            isTopInning={gameState?.isTopInning ?? true}
            runners={gameState?.runners ?? { b1: null, b2: null, b3: null }}
            gameId={gameId ?? undefined}
            userId={userId}
            fatigueLevel={gameState?.active_pitcher?.fatigue_level ?? 0}
            pitchCount={gameState?.active_pitcher?.pitch_count ?? 0}
            onPitcherChanged={(newPitcher) => {
              console.log('🔄 [onPitcherChanged] Fallback local recibido:', newPitcher?.name);
              // El WS PITCHER_CHANGED es la fuente principal.
              // Este callback actualiza localmente en caso de que el WS llegue tarde.
              if (!newPitcher) return;
              setPitcherCard({
                id: newPitcher.id,
                name: newPitcher.name,
                number: newPitcher.number,
                overall: newPitcher.overall,
                position: newPitcher.position,
                rarity: newPitcher.rarity || 'COMMON',
                team: newPitcher.team || '',
                role: 'PITCHER',
                photo: newPitcher.photo,
                repertoire: newPitcher.repertoire || [],
                stats: newPitcher.stats || [],
                pitch_count: 0,
                fatigue_level: 0,
              });
              const rep = newPitcher.repertoire || [];
              if (rep.length > 0 && rep[0]?.pitch_type) {
                setSelectedPitch(rep[0].pitch_type);
              }
            }}
          />
        </div>

        {/* PANEL DERECHO - Siempre STRIKEOUTS del pitcher (Responsive) */}
        <div className="relative z-10 w-full md:w-[450px] md:flex-shrink-0 order-2 md:order-3 overflow-y-auto max-h-[40vh] md:max-h-full">
          <div className="bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded p-1 sm:p-2 md:p-3 text-xs md:text-sm flex flex-col gap-2 sm:gap-3">
            {/* PITCHER STAMINA BAR - Nueva sección arriba de strikeouts */}
            {(() => {
              const staminarDebugData = {
                pitchCount: gameState?.active_pitcher?.pitch_count,
                fatigueLevel: gameState?.active_pitcher?.fatigue_level,
                totalInnings: gameState?.totalInnings,
                activePitcherId: gameState?.activePitcherId,
                activePitcherName: gameState?.active_pitcher?.name,
              };
              console.log('📊 [StadiumShowcaseScreen - STAMINA DATA]', staminarDebugData);
              return null;
            })()}
            <PitcherStaminaBar
              pitchCount={gameState?.active_pitcher?.pitch_count || 0}
              fatigueLevel={gameState?.active_pitcher?.fatigue_level || 0}
              totalInnings={gameState?.totalInnings || 9}
              basePitcherStats={{
                velocidad: gameState?.active_pitcher?.stats?.find((s: any) => s.label === 'VELO')?.val || 75,
                control: gameState?.active_pitcher?.stats?.find((s: any) => s.label === 'CTRL')?.val || 75,
                movimiento: gameState?.active_pitcher?.stats?.find((s: any) => s.label === 'MVTO')?.val || 75,
              }}
            />

            {/* STRIKEOUTS COUNTER */}
            <div>
              <div className="text-[9px] sm:text-xs text-[#C5A059] font-bold mb-0.5 sm:mb-1 px-1">
                🔥 K's
              </div>
              <GameStatsPanel
                lineup={[]}
                stats={{}}
                isPitcher={true}
                pitcherStrikeouts={getPitcherStrikeouts()}
                pitcherName={getActivePitcherName()}
                animateStrikeout={strikeoutAnimationTrigger}
              />
            </div>
          </div>
        </div>
      </main>
      )}

      {/* COMPONENTE MODULAR DE ANIMACIONES DE MAZO Y ZOOM 3D */}


      {/* Overlay de resultado de jugada (con 1 seg de delay antes de aparecer) */}
      {!showGameIntro && (
      <PlayResultOverlay
        resultText={lastResult?.text ?? null}
        resultEvent={lastResult?.event ?? null}
        resultTs={lastResult?.ts ?? null}
        delayMs={1000}
      />
      )}

      {/* Mazo táctico en mano */}
      {!showGameIntro && (
      <TacticalHand
        tacticalHand={tacticalHand}
        selectedTacticalId={selectedTacticalId}
        role={role}
        isIBB={selectedPitch === 'IBB'}
        disabled={isAwaitingResult || inningTransition?.visible || (role === 'PITCHER' && !pitcherCard)}
        onSelectTactical={(id: string) =>
          setSelectedTacticalId(selectedTacticalId === id ? null : id)
        }
        onSubmitPlay={handleSubmitPlay}
      />
      )}

      {/* Modal de Finalizar Partido */}
      <QuitGameModal
        isOpen={showQuitModal}
        onConfirm={handleQuitGame}
        onCancel={() => setShowQuitModal(false)}
        isLoading={isQuittingGame}
      />
    </div>
  );
};