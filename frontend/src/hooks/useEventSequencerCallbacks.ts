import { useEffect, useCallback } from 'react';
import React from 'react';

/**
 * Hook para registrar todos los callbacks del event sequencer
 * Mantiene el estado sincronizado con las etapas de la secuencia
 * 
 * ⚠️ CRITICAL: Los callbacks se registran UNA SOLA VEZ por sesión
 * Cambios en gameState no deben causar re-registro de callbacks
 * porque el payload contiene todos los datos necesarios
 */
export const useEventSequencerCallbacks = (
  onStep: (stepName: string, callback: (payload: any) => void) => void,
  setIsModalVisible: (v: boolean) => void,
  setDeferredGameState: (v: any) => void,
  gameState: any,
  setModalEventData: (v: any) => void,
  setIsAwaitingResult: (v: boolean) => void,
) => {
  // Guardar gameState en un ref para que pueda ser accedido sin ser una dependencia
  const gameStateRef = React.useRef(gameState);
  
  // Contador para garantizar que cada evento tenga un ID único
  // Incluso si dos eventos llegan en el mismo milisegundo
  const eventCounterRef = React.useRef(0);
  
  // Actualizar el ref cuando gameState cambia, pero no causa re-renders
  React.useEffect(() => {
    gameStateRef.current = gameState;
  }, [gameState]);

  // Callback 1: Mostrar modal en delay 0ms
  // ⚠️ CRITICAL: NO incluir gameState en dependencias
  // Cambios en gameState no deben causar re-creación del callback
  // porque eso causa que se pierda la referencia en stepCallbacksRef después de WebSocket updates
  const showModalCallback = useCallback((payload) => {
    console.log('🎬 [SHOW-MODAL] Event:', payload.event);
    console.log('   → Setting isModalVisible to TRUE');
    setIsModalVisible(true);
    // Guardar el estado actual (via ref) para congelar la UI durante el modal
    console.log('   → Freezing gameState via deferredGameState');
    setDeferredGameState(gameStateRef.current);
    
    // Usar un contador + timestamp para garantizar uniqueness
    eventCounterRef.current++;
    const eventId = `${Date.now()}-${eventCounterRef.current}`;
    
    const eventData = {
      text: payload.description || payload.message || 'Evento',
      event: payload.event || 'UNKNOWN',
      ts: eventId,  // ← Usar contador en lugar de solo timestamp
    };
    console.log('   → Setting modalEventData:', eventData);
    setModalEventData(eventData);
    setIsAwaitingResult(true);
  }, [setIsModalVisible, setDeferredGameState, setModalEventData, setIsAwaitingResult]);

  useEffect(() => {
    onStep('show-modal', showModalCallback);
  }, [onStep, showModalCallback]);

  // Callbacks 2-11: placeholder para las etapas adicionales
  // En la versión actual, estos no hacen nada porque el gameState se actualiza vía WebSocket
  const updateScoreCallback = useCallback(() => {
    console.log('   📊 [UPDATE-SCORE] Score will update from WebSocket');
  }, []);

  const updateBatterStatsCallback = useCallback(() => {
    console.log('   📊 [UPDATE-BATTER-STATS] Batter stats will update from WebSocket');
  }, []);

  const updateRunnersCallback = useCallback(() => {
    console.log('   🏃 [UPDATE-RUNNERS] Runners will update from WebSocket');
  }, []);

  const loadNextBatterCallback = useCallback(() => {
    console.log('   🔄 [LOAD-NEXT-BATTER] Next batter will load from WebSocket');
  }, []);

  const updateOutsCallback = useCallback(() => {
    console.log('   ⚾ [UPDATE-OUTS] Outs will update from WebSocket');
  }, []);

  const updatePitcherStatsCallback = useCallback(() => {
    console.log('   🐍 [UPDATE-PITCHER-STATS] Pitcher stats will update from WebSocket');
  }, []);

  const checkInningEndCallback = useCallback(() => {
    console.log('   🔔 [CHECK-INNING-END] Checking inning end condition');
  }, []);

  const updateStrikesCallback = useCallback(() => {
    console.log('   ⚡ [UPDATE-STRIKES] Strikes will update from WebSocket');
  }, []);

  const updateBallsCallback = useCallback(() => {
    console.log('   🎯 [UPDATE-BALLS] Balls will update from WebSocket');
  }, []);

  const updatePitcherCardCallback = useCallback(() => {
    console.log('   🧑‍⚕️ [UPDATE-PITCHER-CARD] Pitcher card will update from WebSocket');
  }, []);

  const resetPitchSelectorCallback = useCallback(() => {
    console.log('   🔄 [RESET-PITCH-SELECTOR] Pitch selector resetting');
  }, []);

  useEffect(() => {
    onStep('update-score', updateScoreCallback);
    onStep('update-batter-stats', updateBatterStatsCallback);
    onStep('update-runners', updateRunnersCallback);
    onStep('load-next-batter', loadNextBatterCallback);
    onStep('update-outs', updateOutsCallback);
    onStep('update-pitcher-stats', updatePitcherStatsCallback);
    onStep('check-inning-end', checkInningEndCallback);
    onStep('update-strikes', updateStrikesCallback);
    onStep('update-balls', updateBallsCallback);
    onStep('update-pitcher-card', updatePitcherCardCallback);
    onStep('reset-pitch-selector', resetPitchSelectorCallback);
  }, [onStep, updateScoreCallback, updateBatterStatsCallback, updateRunnersCallback, 
      loadNextBatterCallback, updateOutsCallback, updatePitcherStatsCallback, 
      checkInningEndCallback, updateStrikesCallback, updateBallsCallback,
      updatePitcherCardCallback, resetPitchSelectorCallback]);

  // Callback para cerrar el modal después de que se ha mostrado
  const closeModalCallback = useCallback(() => {
    console.log('   🚪 [CLOSE-MODAL] Closing modal');
    console.log('   → Setting isModalVisible to FALSE');
    setIsModalVisible(false);
    console.log('   → Setting deferredGameState to NULL');
    setDeferredGameState(null);
    console.log('   ✅ closeModalCallback completed successfully');
  }, [setIsModalVisible, setDeferredGameState]);

  useEffect(() => {
    onStep('close-modal', closeModalCallback);
  }, [onStep, closeModalCallback]);
};
