/**
 * TacticalHand - Main tactical cards display component
 * 
 * Refactored for Propuesta 1:
 * - Split into sub-components (TacticalCardItem, SubmitPlayButton)
 * - Better TypeScript typing with centralized types
 * - Improved documentation and structure
 * - Maintains all original functionality and animations
 * 
 * Features:
 * - Displays hand of tactical cards
 * - Selection with visual feedback
 * - IBB mode detection
 * - Disabled state handling
 * - Fire effect submit button
 * 
 * @component
 * @example
 * <TacticalHand
 *   tacticalHand={cards}
 *   selectedTacticalId="t1"
 *   role="PITCHER"
 *   isIBB={false}
 *   disabled={false}
 *   onSelectTactical={(id) => setSelected(id)}
 *   onSubmitPlay={() => submitPlay()}
 * />
 */

import React from 'react';
import type { TacticalHandProps } from '../../types/stadium.types';
import { TacticalCardItem } from './TacticalCardItem';
import { SubmitPlayButton } from './SubmitPlayButton';

export const TacticalHand: React.FC<TacticalHandProps> = ({
  tacticalHand,
  selectedTacticalId,
  role,
  isIBB,
  disabled = false,
  onSelectTactical,
  onSubmitPlay,
}) => {
  /**
   * Determine button label based on role and mode
   */
  const buttonLabel = isIBB
    ? 'INTENCIONAL ⚾'
    : role === 'PITCHER'
    ? 'LANZAR 🔥'
    : 'BATEAR 💥';

  return (
    <footer className="w-full max-w-6xl mx-auto bg-[#0A0D0F] border border-[#C5A059]/60 p-3.5 flex flex-col md:flex-row justify-between items-center gap-4 mt-3 shadow-2xl">
      {/* HEADER SECTION */}
      <div className="flex flex-col">
        <span className="font-mono text-xs text-[#C5A059] uppercase font-bold">
          CARTAS TÁCTICAS EN MANO
        </span>
        <span className="font-mono text-[10px] text-[#E6DFD3]/70">
          SELECCIONA PARA ACTIVAR TÁCTICA EN LA JUGADA
        </span>
      </div>

      {/* TACTICAL CARDS */}
      <div className="flex gap-3 overflow-x-auto py-1">
        {tacticalHand.map((card) => (
          <TacticalCardItem
            key={card.id}
            card={card}
            isSelected={selectedTacticalId === card.id}
            disabled={disabled}
            onSelect={onSelectTactical}
          />
        ))}
      </div>

      {/* SUBMIT BUTTON */}
      <SubmitPlayButton
        label={buttonLabel}
        disabled={disabled}
        onSubmit={onSubmitPlay}
      />
    </footer>
  );
};

TacticalHand.displayName = 'TacticalHand';
