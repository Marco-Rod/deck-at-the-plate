/**
 * PitchZoneGrid - Main pitch selection component
 * 
 * Refactored for Propuesta 1:
 * - Split into sub-components (PitchSelector, StrikeZoneGrid)
 * - Better TypeScript typing with centralized types
 * - Improved documentation and structure
 * - Maintains all original functionality
 * 
 * Modes:
 * - PITCHER: Shows pitch type selector + strike zone grid
 * - BATTER: Shows only strike zone grid for swing prediction
 * 
 * Special Handling:
 * - IBB (Intentional Base on Balls): Always selectable, disables zone selection
 *   but allows changing to/from other pitch types
 * 
 * @component
 * @example
 * <PitchZoneGrid
 *   role="PITCHER"
 *   selectedZone={5}
 *   selectedPitch="4-SEAM"
 *   onSelectZone={(zone) => setSelectedZone(zone)}
 *   onSelectPitch={(pitch) => setSelectedPitch(pitch)}
 *   repertoire={pitcher.repertoire}
 *   disabled={false}
 * />
 */

import React, { useMemo } from 'react';
import type { PitchZoneGridProps } from '../../types/stadium.types';
import { PitchSelector } from './PitchSelector';
import { StrikeZoneGrid } from './StrikeZoneGrid';

export const PitchZoneGrid: React.FC<PitchZoneGridProps> = ({
  role,
  selectedZone,
  selectedPitch,
  onSelectZone,
  onSelectPitch,
  repertoire,
  disabled = false,
}) => {
  /**
   * Determine available pitches from repertoire or use defaults
   */
  const availablePitches = useMemo(() => {
    if (repertoire && repertoire.length > 0) {
      return repertoire.map((p) => p.pitch_type);
    }
    // Fallback to safe defaults if no repertoire
    return ['4-SEAM', 'SLIDER', 'CHANGE'];
  }, [repertoire]);

  /**
   * Determine if pitcher is in intentional walk mode
   * IBB is always selectable, but it disables zone selection
   */
  const isIBBMode = selectedPitch === 'IBB';

  return (
    <div
      className={`z-10 flex flex-col items-center gap-3 my-auto transition-opacity ${
        disabled ? 'opacity-40 pointer-events-none' : ''
      }`}
    >
      {/* PITCH SELECTOR - Only show for pitcher, but ALWAYS enabled for changing */}
      {role === 'PITCHER' && (
        <PitchSelector
          availablePitches={availablePitches}
          selectedPitch={selectedPitch}
          onSelectPitch={onSelectPitch}
          disabled={disabled}
        />
      )}

      {/* STRIKE ZONE GRID - Disabled only if IBB mode (no zone for intentional walk) */}
      <StrikeZoneGrid
        selectedZone={selectedZone}
        onSelectZone={onSelectZone}
        disabled={disabled || isIBBMode}
      />

      {/* IBB Mode Indicator */}
      {isIBBMode && (
        <div className="text-center px-3 py-2 bg-[#C5A059]/10 border border-[#C5A059]/30 rounded-xs">
          <span className="font-mono text-[9px] text-[#C5A059] uppercase font-bold">
            🏃 Intentional Walk - No Zone Selection
          </span>
        </div>
      )}
    </div>
  );
};

PitchZoneGrid.displayName = 'PitchZoneGrid';
