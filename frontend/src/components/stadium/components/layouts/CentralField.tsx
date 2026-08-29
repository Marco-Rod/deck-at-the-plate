/**
 * CentralField - Central gameplay area organizer
 * 
 * Propuesta 1 Improvements:
 * - gap-4 → gap-6 (+50% spacing for better clarity)
 * - Organized layout with clear sections
 * - Responsive design
 * - Proper component composition
 * 
 * Layout:
 * - GameInfo (top) - B/S/O, bases, inning
 * - Central trio (middle) - Pitcher Card | PitchZoneGrid | Batter Card
 * - Dynamic Message (conditional) - \"El lanzador ya pichó\" message
 * 
 * @component
 * @example
 * <CentralField
 *   role="PITCHER"
 *   pitcherCard={pitcher}
 *   batterCard={batter}
 *   selectedZone={5}
 *   selectedPitch="4-SEAM"
 *   repertoire={pitcher.repertoire}
 *   hasPitched={false}
 *   isAwaitingResult={false}
 *   inningTransition={null}
 *   onSelectZone={(z) => setZone(z)}
 *   onSelectPitch={(p) => setPitch(p)}
 * />
 */

import React, { useState, useEffect } from 'react';
import { GameInfo, PitchZoneGrid } from '../index';
import { PlayerCard } from '../../PlayerCard';
import { ChangePitcherModal } from '../../ChangePitcherModal';
import type { CentralFieldProps } from '../../types/stadium.types';
import { games as gamesApi } from '../../../../utils/api';

export const CentralField: React.FC<CentralFieldProps & {
  gameId?: string;
  userId?: string;
  fatigueLevel?: number;
  pitchCount?: number;
  onPitcherChanged?: (newPitcher: any) => void;
}> = ({
  role,
  pitcherCard,
  batterCard,
  selectedZone,
  selectedPitch,
  repertoire,
  hasPitched,
  isAwaitingResult,
  inningTransition,
  onSelectZone,
  onSelectPitch,
  balls = 0,
  strikes = 0,
  outs = 0,
  currentInning = 1,
  totalInnings = 9,
  isTopInning = true,
  runners = { b1: null, b2: null, b3: null },
  gameId,
  userId,
  fatigueLevel = 0,
  pitchCount = 0,
  onPitcherChanged,
}) => {
  const [showChangePitcherModal, setShowChangePitcherModal] = useState(false);
  const [availablePitchers, setAvailablePitchers] = useState<any[]>([]);
  const [isLoadingPitchers, setIsLoadingPitchers] = useState(false);
  const [showMinPitchesHint, setShowMinPitchesHint] = useState(false);

  const MIN_PITCHES_TO_CHANGE = 5;
  const canChangePitcher = pitchCount >= MIN_PITCHES_TO_CHANGE;

  const handleClickPitcherCard = () => {
    if (!canChangePitcher) {
      // Mostrar hint brevemente
      setShowMinPitchesHint(true);
      setTimeout(() => setShowMinPitchesHint(false), 2000);
      return;
    }
    console.log(`🔓 [MODAL ABIERTO] Modal de sustitución de lanzador abierto`);
    console.log(`   gameId=${gameId}, userId=${userId}`);
    setShowChangePitcherModal(true);
  };

  // Cargar pitchers disponibles cuando se abre el modal
  useEffect(() => {
    if (showChangePitcherModal && gameId && userId) {
      loadAvailablePitchers();
    }
  }, [showChangePitcherModal, gameId, userId]);

  const loadAvailablePitchers = async () => {
    if (!gameId || !userId) {
      return;
    }
    try {
      setIsLoadingPitchers(true);
      console.log(`📡 [SOLICITUD] GET /api/v1/games/${gameId}/available-pitchers?user_id=${userId}`);
      const response = await gamesApi.getAvailablePitchers(gameId, userId);
      const pitchers = response?.available_pitchers || [];
      setAvailablePitchers(pitchers);
    } catch (error) {
      setAvailablePitchers([]);
    } finally {
      setIsLoadingPitchers(false);
    }
  };

  const handleChangePitcher = async (newPitcherId: string) => {
    if (!gameId) return;

    try {
      const response = await gamesApi.changePitcher(gameId, { new_pitcher_id: newPitcherId }, userId);
      
      // Notificar al componente padre
      if (onPitcherChanged && response?.active_pitcher) {
        onPitcherChanged(response.active_pitcher);
      }
      
      setShowChangePitcherModal(false);
    } catch (error) {
      throw error;
    }
  };
  return (
    <div className="relative z-10 w-full flex flex-col items-center gap-1 sm:gap-2 md:gap-3 lg:gap-6 px-0.5 sm:px-1 md:px-2">
      {/* GAME INFO - Responsive width */}
      <div className="w-full flex justify-center px-0.5 sm:px-1">
        <div className="w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-2xl">
          <GameInfo
            balls={balls}
            strikes={strikes}
            outs={outs}
            currentInning={currentInning}
            totalInnings={totalInnings}
            isTopInning={isTopInning}
            role={role}
            runners={runners}
          />
        </div>
      </div>

      {/* CENTRAL TRIO: Pitcher | Grid | Batter - Responsive */}
      <div className="w-full flex flex-col sm:flex-row justify-center items-center gap-1 sm:gap-2 md:gap-4 lg:gap-6 flex-wrap">
        {/* PITCHER CARD - Responsive sizing */}
        <div className="flex-shrink-0 w-24 sm:w-32 md:w-40 lg:w-56 flex items-start justify-center">
          <div className="relative">
            <PlayerCard
              player={pitcherCard}
              role="PITCHER"
              disablePulse={true}
              size="sm"
              fatigueLevel={fatigueLevel}
              onClickPitcher={role === 'PITCHER' ? handleClickPitcherCard : undefined}
            />

            {/* Indicador de lanzamientos mínimos — visible cuando no puede cambiarse */}
            {role === 'PITCHER' && !canChangePitcher && pitchCount > 0 && (
              <div className="absolute -bottom-5 left-0 right-0 flex justify-center pointer-events-none">
                <span className="text-[9px] font-mono text-[#A89968]/70 whitespace-nowrap">
                  {MIN_PITCHES_TO_CHANGE - pitchCount} lanz. para cambio
                </span>
              </div>
            )}

            {/* Hint animado cuando intenta abrir el modal sin cumplir el mínimo */}
            {showMinPitchesHint && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                <div className="bg-[#0F1419]/95 border border-[#C5A059]/60 rounded-lg px-2 py-1.5 text-center shadow-lg">
                  <p className="text-[10px] font-mono text-[#C5A059] font-bold leading-tight">
                    Mín. {MIN_PITCHES_TO_CHANGE} lanzamientos
                  </p>
                  <p className="text-[9px] font-mono text-[#A89968] leading-tight">
                    Faltan {MIN_PITCHES_TO_CHANGE - pitchCount}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* PITCH ZONE GRID - Responsive */}
        <div className="flex-shrink-0 w-full sm:w-auto">
          <PitchZoneGrid
            role={role}
            selectedZone={selectedZone}
            selectedPitch={selectedPitch}
            onSelectZone={onSelectZone}
            onSelectPitch={onSelectPitch}
            repertoire={repertoire}
            disabled={isAwaitingResult || inningTransition?.visible}
          />
        </div>

        {/* BATTER CARD - Responsive sizing */}
        <div className="flex-shrink-0 w-24 sm:w-32 md:w-40 lg:w-56 flex items-start justify-center">
          <PlayerCard
            player={batterCard}
            role="BATTER"
            disablePulse={true}
            size="sm"
          />
        </div>
      </div>

      {/* DYNAMIC MESSAGE - Responsive text size */}
      {hasPitched && role === 'BATTER' && (
        <div className="mt-1 sm:mt-2 bg-[#C5A059]/90 text-[#0A0D0F] px-3 sm:px-4 md:px-6 py-1 sm:py-2 font-mono text-[10px] sm:text-xs md:text-sm font-bold z-20 animate-bounce rounded-sm shadow-lg text-center">
          ¡El lanzador ya pichó! Selecciona tu swing.
        </div>
      )}

      {/* ⭐ NUEVO: Modal para cambiar lanzador */}
      <ChangePitcherModal
        isOpen={showChangePitcherModal}
        onClose={() => setShowChangePitcherModal(false)}
        currentPitcher={pitcherCard}
        availablePitchers={availablePitchers}
        onConfirm={handleChangePitcher}
        isLoading={isLoadingPitchers}
      />
    </div>
  );
};

CentralField.displayName = 'CentralField';
