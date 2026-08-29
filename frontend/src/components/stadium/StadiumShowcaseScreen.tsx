import React, { useState } from 'react';
import { useStadiumSocket, parseStateData } from '../../hooks/useStadiumSocket';
import { useEventSequencer, EVENT_SEQUENCES, EVENT_DURATIONS } from '../../hooks/useEventSequencer';
import { useGameStateSetup } from '../../hooks/useGameStateSetup';
import { useModalSequencing } from '../../hooks/useModalSequencing';
import { useCardLoading } from '../../hooks/useCardLoading';
import { useTacticalControls } from '../../hooks/useTacticalControls';
import { useEventSequencerCallbacks } from '../../hooks/useEventSequencerCallbacks';
import { GameplayModals } from './GameplayModals';
import { GameplayInterface } from './GameplayInterface';
import { RivalPitcherChangeModal } from './RivalPitcherChangeModal';
import { PlayResultOverlay } from './PlayResultOverlay';
import { games as gamesApi, cards as cardsApi, user as userApi } from '../../utils/api';
import { normalizeEventName } from '../../utils/eventNormalizer';

import type { PlayerRole } from '../../types/stadium';

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
  // ═══════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════
  const [selectedPitch, setSelectedPitch] = useState('4-SEAM');
  const [selectedSwing, setSelectedSwing] = useState<'NORMAL' | 'POWER' | 'TAKE' | 'BUNT'>('NORMAL');
  const [selectedZone, setSelectedZone] = useState(5);
  const [selectedTacticalId, setSelectedTacticalId] = useState<string | null>(null);
  const [hasPitched, setHasPitched] = useState(false);
  
  const [showGameIntro, setShowGameIntro] = useState(true);
  const [showGameOverModal, setShowGameOverModal] = useState(false);
  const [inningTransition, setInningTransition] = useState<any>(null);
  
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [deferredGameState, setDeferredGameState] = useState<any>(null);
  const [modalEventData, setModalEventData] = useState<any>(null);
  
  const [showRivalPitcherChangeModal, setShowRivalPitcherChangeModal] = useState(false);
  const [showRivalPitcherChangeAck, setShowRivalPitcherChangeAck] = useState(false);
  const [rivalPitcherChangeData, setRivalPitcherChangeData] = useState<any>(null);
  
  const [userTeam, setUserTeam] = useState<any>(null);
  const [userLineupCards, setUserLineupCards] = useState<any[]>([]);
  const [cpuLineupCards, setCpuLineupCards] = useState<any[]>([]);

  // ═══════════════════════════════════════════════════════════════
  // EVENT SEQUENCER
  // ═══════════════════════════════════════════════════════════════
  const { onStep, enqueueEvent } = useEventSequencer();

  // ═══════════════════════════════════════════════════════════════
  // WEBSOCKET
  // ═══════════════════════════════════════════════════════════════
  const {
    gameState,
    lastResult,
    inningCompleted,
    isConnected,
    wsError,
    sendPitch,
    sendSwing,
    sendTactic,
  } = useStadiumSocket(gameId, userId, {
    onPlayResolved: (payload: any) => {
      const normalizedEvent = normalizeEventName(payload.event);
      console.log(`🎯 [ENQUEUE EVENT] original="${payload.event}" → normalized="${normalizedEvent}" | valid=${Object.keys(EVENT_SEQUENCES).includes(normalizedEvent)}`);
      enqueueEvent(normalizedEvent as keyof typeof EVENT_SEQUENCES, payload);
    },
    onPitcherChanged: (payload: any) => {
      console.log('🔔 [RIVAL PITCHER CHANGE] Evento recibido. Abriendo modal...');
      console.log(`   oldPitcher: ${payload.old_pitcher_data?.name}`);
      console.log(`   newPitcher: ${payload.new_pitcher?.name}`);
      setRivalPitcherChangeData({
        oldPitcher: payload.old_pitcher_data,
        newPitcher: payload.new_pitcher,
      });
      setShowRivalPitcherChangeAck(true);
    },
  });

  // ═══════════════════════════════════════════════════════════════
  // COMPUTED STATE
  // ═══════════════════════════════════════════════════════════════
  const userRole = gameState?.userRole || ('HOME' as 'HOME' | 'AWAY');
  const displayedGameState = isModalVisible && deferredGameState ? deferredGameState : gameState;

  const role: PlayerRole = !gameState 
    ? 'BATTER'
    : (() => {
      if (userRole === 'HOME') {
        return gameState.isTopInning ? 'PITCHER' : 'BATTER';
      } else {
        return gameState.isTopInning ? 'BATTER' : 'PITCHER';
      }
    })();

  // ═══════════════════════════════════════════════════════════════
  // HOOKS
  // ═══════════════════════════════════════════════════════════════
  useGameStateSetup(gameState, userRole, cardsApi, setUserLineupCards, setCpuLineupCards, userTeam, gameState?.rivalTeamName);
  
  useModalSequencing(gameState, lastResult, inningCompleted, false, setShowGameIntro, setShowGameOverModal, setInningTransition, () => {}, EVENT_SEQUENCES, EVENT_DURATIONS);
  
  const { pitcherCard, cpuPitcherCard, batterCard, setPitcherCard, setCpuPitcherCard, setBatterCard } = useCardLoading(gameState, userRole, userTeam, userLineupCards, cardsApi);
  
  const { isProcessing, isQuittingGame, showQuitModal, setShowQuitModal, handleSubmitPlay, handleQuitGame } = useTacticalControls(
    gameId, userId, false, inningTransition, role, pitcherCard, selectedZone, selectedPitch, selectedSwing, selectedTacticalId,
    setSelectedTacticalId, () => {}, sendPitch, sendSwing, sendTactic, onBack
  );
  
  useEventSequencerCallbacks(onStep, setIsModalVisible, setDeferredGameState, gameState, setModalEventData, () => {});

  React.useEffect(() => {
    userApi.getTeam(userId).then(setUserTeam).catch(() => null);
  }, [userId]);

  // 🔍 DEBUG: Monitor isModalVisible changes
  React.useEffect(() => {
    console.log('📊 [STADIUM] isModalVisible STATE CHANGED:', {
      isModalVisible,
      modalEventData: modalEventData?.event,
      deferredGameState: deferredGameState?.currentInning,
    });
  }, [isModalVisible, modalEventData, deferredGameState]);

  // ═══════════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════════
  const getPitcherStrikeouts = () => gameState?.pitcher_strikeouts?.[gameState?.activePitcherId] ?? 0;
  
  const getWinningPitcherInfo = () => {
    if (!gameState?.isGameOver) return { name: undefined, strikeouts: 0 };
    
    // Determinar si el usuario ganó (no si el pitcher actual es el del usuario)
    const userWon = 
      (userRole === 'HOME' && gameState.homeScore > gameState.awayScore) ||
      (userRole === 'AWAY' && gameState.awayScore > gameState.homeScore);
    
    // Si el usuario ganó, el pitcher ganador es el del usuario; si no, es el de la CPU
    const winningPitcher = userWon ? pitcherCard : cpuPitcherCard;
    
    // Obtener los strikeouts del pitcher ganador (no del pitcher actual)
    const winningPitcherId = winningPitcher?.id;
    const strikeouts = gameState?.pitcher_strikeouts?.[winningPitcherId] ?? 0;
    
    return { name: winningPitcher?.name || 'Pitcher', strikeouts };
  };

  const getActivePitcherName = () => {
    if (!gameState?.activePitcherId) return 'Pitcher';
    if (pitcherCard?.id === gameState.activePitcherId) return pitcherCard.name || 'Pitcher';
    return cpuPitcherCard?.name || 'Pitcher';
  };

  const getBattingLineup = () => {
    if (!gameState) return [];
    const isBattingUser = (userRole === 'HOME' && gameState.isTopInning) || (userRole === 'AWAY' && !gameState.isTopInning);
    return isBattingUser ? userLineupCards : cpuLineupCards;
  };

  const getBattingLineupLabel = () => {
    if (!gameState) return 'LINEUP';
    const isBattingUser = (userRole === 'HOME' && gameState.isTopInning) || (userRole === 'AWAY' && !gameState.isTopInning);
    return isBattingUser ? 'YOUR LINEUP' : 'CPU LINEUP';
  };

  const handleClickRivalPitcher = async () => {
    if (!cpuPitcherCard || !gameState?.gameId) return;
    console.log('🎯 [RIVAL PITCHER CLICK] Opening pitcher change modal and loading available pitchers');
    setShowRivalPitcherChangeModal(true);
    
    try {
      const response = await gamesApi.getRivalAvailablePitchers(gameState.gameId);
      const availablePitchers = response?.available_pitchers || [];
      console.log(`📋 ${availablePitchers.length} rival pitchers loaded`);
      
      setRivalPitcherChangeData({
        oldPitcher: cpuPitcherCard,
        newPitcher: null,
        availablePitchers: availablePitchers,
      });
    } catch (error) {
      console.error('❌ Error loading rival pitchers:', error);
      setRivalPitcherChangeData({
        oldPitcher: cpuPitcherCard,
        newPitcher: null,
        availablePitchers: [],
      });
    }
  };

  const handleAcknowledgePitcherChange = async () => {
    try {
      console.log('✅ [ACK PITCHER CHANGE] Enviando confirmación al servidor...');
      await gamesApi.acknowledgePitcherChange(gameId);
      console.log('✅ [ACK PITCHER CHANGE] Confirmación recibida. El juego continúa.');
      setShowRivalPitcherChangeAck(false);
      setRivalPitcherChangeData(null);
    } catch (error) {
      console.error('❌ [ACK PITCHER CHANGE] Error:', error);
      // Intentar de nuevo o mostrar error al usuario
    }
  };

  const tacticalHand = [
    { id: 't1', name: 'RECTA FUEGO', cost: 1, desc: '+10 VEL en zona alta', type: 'PITCH BOOST', color: 'border-red-500/80 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]', icon: '🔥' },
    { id: 't2', name: 'PICONAZO', cost: 2, desc: 'Provoca Whiff fuera de zona', type: 'SPECIAL', color: 'border-[#C5A059] text-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)]', icon: '〰️' },
    { id: 't3', name: 'PITCHOUT', cost: 1, desc: 'Sorprende a corredor en robo', type: 'DEFENSE', color: 'border-blue-400/80 text-blue-300 shadow-[0_0_15px_rgba(96,165,250,0.3)]', icon: '🏃' },
    { id: 't4', name: 'TOQUE SUICIDA', cost: 2, desc: 'Asegura carrera desde 3B', type: 'OFFENSE', color: 'border-emerald-500/80 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]', icon: '🏏' },
  ];

  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════
  return (
    <div className="relative w-full h-full">
      <GameplayModals
        showGameIntro={showGameIntro && userLineupCards.length > 0}
        gameState={gameState}
        userTeam={userTeam}
        userLineupCards={userLineupCards}
        pitcherCard={pitcherCard}
        cpuPitcherCard={cpuPitcherCard}
        cpuLineupCards={cpuLineupCards}
        onPlayBall={() => setShowGameIntro(false)}
        showGameOverModal={showGameOverModal}
        userRole={userRole}
        getWinningPitcherInfo={getWinningPitcherInfo}
        onReturnToLobby={onBack}
        inningTransition={inningTransition}
        displayedGameState={displayedGameState}
      />

      {isModalVisible && modalEventData && (
        <PlayResultOverlay
          resultText={modalEventData.text}
          resultEvent={modalEventData.event}
          resultTs={modalEventData.ts}
        />
      )}
      {!isModalVisible && console.log('❌ [STADIUM] Modal NOT rendered - isModalVisible is FALSE')}
      {!modalEventData && console.log('❌ [STADIUM] Modal NOT rendered - modalEventData is NULL')}

      <GameplayInterface
        showGameIntro={showGameIntro}
        gameState={gameState}
        displayedGameState={displayedGameState}
        userTeam={userTeam}
        userId={userId}
        gameId={gameId}
        userRole={userRole}
        role={role}
        pitcherCard={pitcherCard}
        batterCard={batterCard}
        cpuPitcherCard={cpuPitcherCard}
        userLineupCards={userLineupCards}
        cpuLineupCards={cpuLineupCards}
        lastResult={lastResult}
        inningTransition={inningTransition}
        isConnected={isConnected}
        wsError={wsError}
        onBack={onBack}
        selectedZone={selectedZone}
        selectedPitch={selectedPitch}
        selectedSwing={selectedSwing}
        selectedTacticalId={selectedTacticalId}
        hasPitched={hasPitched}
        setSelectedZone={setSelectedZone}
        setSelectedPitch={setSelectedPitch}
        setSelectedSwing={setSelectedSwing}
        setSelectedTacticalId={setSelectedTacticalId}
        setPitcherCard={setPitcherCard}
        isAwaitingResult={false}
        isProcessing={isProcessing}
        handleSubmitPlay={handleSubmitPlay}
        showQuitModal={showQuitModal}
        setShowQuitModal={setShowQuitModal}
        handleQuitGame={handleQuitGame}
        isQuittingGame={isQuittingGame}
        getBattingLineup={getBattingLineup}
        getBattingLineupLabel={getBattingLineupLabel}
        getPitcherStrikeouts={getPitcherStrikeouts}
        getActivePitcherName={getActivePitcherName}
        tacticalHand={tacticalHand}
        rivalPitcherChangeData={rivalPitcherChangeData}
        showRivalPitcherChangeModal={showRivalPitcherChangeModal}
        setShowRivalPitcherChangeModal={setShowRivalPitcherChangeModal}
        onClickRivalPitcher={handleClickRivalPitcher}
      />

      {/* ⭐ NUEVO: Modal de confirmación de cambio de pitcher del rival */}
      <RivalPitcherChangeModal
        isOpen={showRivalPitcherChangeAck}
        oldPitcher={rivalPitcherChangeData?.oldPitcher}
        newPitcher={rivalPitcherChangeData?.newPitcher}
        onAccept={handleAcknowledgePitcherChange}
      />
    </div>
  );
};

StadiumShowcaseScreen.displayName = 'StadiumShowcaseScreen';
