import React, { useState, useEffect, useRef } from 'react';
import { Scoreboard } from './Scoreboard';
import { GameInfo } from './GameInfo';
import { PitchZoneGrid } from './PitchZoneGrid';
import { PlayerCard } from './PlayerCard';
import { TacticalHand } from './TacticalHand';
import { PlayResultOverlay } from './PlayResultOverlay';
import { GameOverModal } from './GameOverModal';
import { InningTransitionModal } from './InningTransitionModal';
import { GameIntroModal } from './GameIntroModal'; // ⭐ NUEVO
import { GameStatsPanel } from './GameStatsPanel'; // ⭐ NUEVO
import { GameplayDeckAndReveal } from './GameplayDeckAndReveal';
import { useStadiumSocket } from '../../hooks/useStadiumSocket';
import { cards as cardsApi, user as userApi } from '../../utils/api';

import {
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
  
  const lastProcessedInningCompletedRef = useRef<number | null>(null);

  const { gameState, lastResult, inningCompleted, hasPitched, isConnected, sendPitch, sendSwing, sendTactic } =
    useStadiumSocket(gameId ?? '', userId);

  // ⭐ NUEVO: Calcular strikeouts del pitcher activo desde WebSocket
  const getPitcherStrikeouts = () => {
    // Si no hay strikeouts, retornar 0
    if (!gameStats.pitchers || Object.keys(gameStats.pitchers).length === 0) {
      console.log('❌ [SO COUNTER] No pitcher data:', gameStats);
      return 0;
    }
    
    // Si el pitcher activo no está en los datos, retornar 0
    const activePitcherId = gameState?.activePitcherId;
    if (!activePitcherId) {
      console.log('❌ [SO COUNTER] No activePitcherId');
      return 0;
    }
    
    // Obtener strikeouts del pitcher activo
    const so = gameStats.pitchers[activePitcherId] ?? 0;
    console.log('✅ [SO COUNTER]', {
      activePitcherId,
      strikeouts: so,
      allPitchers: Object.keys(gameStats.pitchers),
    });
    return so;
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
    if (gameState?.pitcher_strikeouts || gameState?.batter_stats) {
      console.log('📊 [UPDATED STATS FROM WEBSOCKET]:', {
        pitchers: gameState.pitcher_strikeouts,
        batters: Object.keys(gameState.batter_stats || {}).length,
        batter_stats_sample: gameState.batter_stats ? Object.entries(gameState.batter_stats).slice(0, 2) : [],
      });
      setGameStats({
        pitchers: gameState.pitcher_strikeouts || {},
        batters: gameState.batter_stats || {},
      });
    }
  }, [gameState?.pitcher_strikeouts, gameState?.batter_stats]);

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

  // Detecta cuando la entrada termina (backend envía inning_completed=true)
  // y muestra el modal de transición con timing correcto.
  useEffect(() => {
    if (!inningCompleted || !gameState) return;

    // Evitar procesar el mismo inningCompleted dos veces usando ref
    if (lastProcessedInningCompletedRef.current === inningCompleted.ts) {
      return;
    }

    lastProcessedInningCompletedRef.current = inningCompleted.ts;

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
    if (!gameState) return '📊 LINEUP';
    
    const isBattingUser = 
      (userRole === 'HOME' && !gameState.isTopInning) ||
      (userRole === 'AWAY' && gameState.isTopInning);
    
    return isBattingUser ? '📊 YOUR LINEUP' : '📊 CPU LINEUP';
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
    if (gameState?.activePitcherId) {
      cardsApi.getCard(gameState.activePitcherId)
        .then((c: any) => {
          if (c) {
            setPitcherCard({
              id: c.id,
              name: c.name,
              number: c.number || '17',
              overall: c.overall || 99,
              position: c.position || 'SP',
              photo: c.photo,
              repertoire: c.repertoire || [],
              stats: [
                { label: 'VEL', val: c.velocity || 98 },
                { label: 'CTL', val: c.control || 88 },
                { label: 'MOV', val: c.movement || 92 },
                { label: 'STA', val: c.stamina || 80 },
              ]
            });
            if (c.repertoire && c.repertoire.length > 0) {
              setSelectedPitch(c.repertoire[0].pitch_type);
            }
          }
        })
        .catch(() => null);
    }

    if (gameState?.activeBatterId) {
      cardsApi.getCard(gameState.activeBatterId)
        .then((c: any) => {
          if (c) {
            setBatterCard({
              id: c.id,
              name: c.name,
              number: c.number || '17',
              overall: c.overall || 99,
              position: c.position || 'DH',
              photo: c.photo,
              stats: [
                { label: 'PWR', val: c.power || 98 },
                { label: 'CON', val: c.contact || 92 },
                { label: 'VIS', val: c.vision || 80 },
                { label: 'SPD', val: c.speed || 80 },
              ]
            });
          }
        })
        .catch(() => null);
    }
  }, [gameState?.activePitcherId, gameState?.activeBatterId]);

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
        return (
          <GameOverModal
            winnerMessage={gameState.winnerMessage}
            homeScore={gameState.homeScore}
            awayScore={gameState.awayScore}
            homeTeamName={homeTeamDisplay}
            awayTeamName={awayTeamDisplay}
            userRole={userRole}
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
            onClick={onBack}
            className="bg-[#0A0D0F] border border-[#C5A059] px-4 py-2 font-mono text-xs text-[#C5A059] font-bold cursor-pointer hover:bg-[#1A3323]"
          >
            ⚙️ LOBBY
          </button>
        </div>
      </header>
      )}

      {/* Marcador */}
      {!showGameIntro && gameState && (() => {
        const homeTeamDisplay = userRole === 'HOME' ? userTeam?.short_name : `${gameState?.rivalTeamName || 'YANKEES'} (CPU)`;
        const awayTeamDisplay = userRole === 'HOME' ? `${gameState?.rivalTeamName || 'YANKEES'} (CPU)` : userTeam?.short_name;
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
        className="w-[95%] mx-auto border-2 border-[#C5A059]/50 p-1 relative flex justify-between items-center min-h-[500px] shadow-2xl overflow-hidden rounded-sm gap-1 mt-1"
      >
        {/* Capa oscura translúcida */}
        <div className="absolute inset-0 bg-[#0A0D0F]/60 pointer-events-none" />

        {/* PANEL IZQUIERDO - Siempre el LINEUP del bateador */}
        <div className="relative z-10 w-80 flex-shrink-0">
          <div className="bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded p-2">
            <div className="text-xs text-[#C5A059] font-bold mb-1 px-1">
              {getBattingLineupLabel()}
            </div>
            <GameStatsPanel
              lineup={getBattingLineup()}
              stats={gameStats?.batters || {}}
              isPitcher={false}
            />
          </div>
        </div>

        {/* CONTENEDOR CENTRAL - Campo de juego */}
        <div className="relative z-10 flex-1 flex flex-col items-center gap-1">
          {/* GameInfo - B/S/O, Inning, Bases */}
          <GameInfo 
            balls={gameState?.balls || 0}
            strikes={gameState?.strikes || 0}
            outs={gameState?.outs || 0}
            currentInning={gameState?.currentInning || 1}
            totalInnings={gameState?.totalInnings || 9}
            isTopInning={gameState?.isTopInning ?? true}
            role={role}
            runners={gameState?.runners || { b1: null, b2: null, b3: null }}
          />

          <div className="w-full flex justify-center items-center gap-4">
            <PlayerCard player={pitcherCard} role="PITCHER" />
            
            <PitchZoneGrid
              role={role}
              selectedZone={selectedZone}
              selectedPitch={selectedPitch}
              onSelectZone={setSelectedZone}
              onSelectPitch={setSelectedPitch}
              repertoire={pitcherCard?.repertoire}
              disabled={isAwaitingResult || inningTransition?.visible || (role === 'PITCHER' && !pitcherCard)}
            />
            
            <PlayerCard player={batterCard} role="BATTER" />
          </div>

          {hasPitched && role === 'BATTER' && (
            <div className="mt-2 bg-[#C5A059] text-[#0A0D0F] px-4 py-1 font-mono text-xs font-bold z-20 animate-bounce">
              ¡El lanzador ya pichó! Selecciona tu swing.
            </div>
          )}
        </div>

        {/* PANEL DERECHO - Siempre STRIKEOUTS del pitcher */}
        <div className="relative z-10 w-80 flex-shrink-0">
          <div className="bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded p-2">
            <div className="text-xs text-[#C5A059] font-bold mb-1 px-1">
              🔥 STRIKEOUTS
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
    </div>
  );
};