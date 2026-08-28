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

import React, { useState } from 'react';
import { GameInfo, PitchZoneGrid } from '../index';
import { PlayerCard } from '../../PlayerCard';
import { ChangePitcherModal } from '../../ChangePitcherModal';
import type { CentralFieldProps } from '../../types/stadium.types';

export const CentralField: React.FC<CentralFieldProps> = ({
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
}) => {
  const [showChangePitcherModal, setShowChangePitcherModal] = useState(false);
  
  // ⭐ NUEVO: Lista de lanzadores disponibles (se obtendría del estado del juego)
  // Por ahora es un placeholder - se actualizará con datos reales del backend
  const availablePitchers: any[] = [];
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
          <PlayerCard
            player={pitcherCard}
            role="PITCHER"
            disablePulse={true}
            size="sm"
            fatigueLevel={0} // ⭐ TODO: Pasar desde gameState
            onClickPitcher={() => setShowChangePitcherModal(true)}
          />
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
        onConfirm={async (newPitcherId) => {
          // ⭐ TODO: Implementar llamada al backend para cambiar pitcher
          console.log('Cambiar pitcher a:', newPitcherId);
        }}
      />
    </div>
  );
};

CentralField.displayName = 'CentralField';
