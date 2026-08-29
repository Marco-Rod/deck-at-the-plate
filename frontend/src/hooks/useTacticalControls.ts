import { useState, useCallback } from 'react';

/**
 * Hook para manejar controles tácticos y envío de jugadas
 */
export const useTacticalControls = (
  gameId: string | null,
  userId: string,
  isAwaitingResult: boolean,
  inningTransition: any,
  role: 'PITCHER' | 'BATTER',
  pitcherCard: any,
  selectedZone: string,
  selectedPitch: string,
  selectedSwing: string,
  selectedTacticalId: string | null,
  setSelectedTacticalId: (id: string | null) => void,
  setIsAwaitingResult: (v: boolean) => void,
  sendPitch: (zone: string, pitch: string) => Promise<void>,
  sendSwing: (swing: string, zone: string, pitch: string) => Promise<void>,
  sendTactic: (id: string, role: 'PITCHER' | 'BATTER') => Promise<void>,
  onBack: () => void,
) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isQuittingGame, setIsQuittingGame] = useState(false);
  const [showQuitModal, setShowQuitModal] = useState(false);

  const handleSubmitPlay = useCallback(async () => {
    if (isAwaitingResult || inningTransition?.visible) return;
    setIsAwaitingResult(true);
    setIsProcessing(true);
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
      setIsAwaitingResult(false);
    } finally {
      setIsProcessing(false);
    }
  }, [isAwaitingResult, inningTransition?.visible, role, selectedTacticalId, selectedZone, selectedPitch, selectedSwing, sendPitch, sendSwing, sendTactic, setIsAwaitingResult, setSelectedTacticalId]);

  const handleQuitGame = useCallback(async () => {
    setIsQuittingGame(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 300));
      onBack();
    } catch (error) {
      console.error('Error al finalizar el partido:', error);
      setIsQuittingGame(false);
    }
  }, [onBack]);

  return {
    isProcessing,
    isQuittingGame,
    showQuitModal,
    setShowQuitModal,
    handleSubmitPlay,
    handleQuitGame,
  };
};
