/**
 * PitchZoneGrid - Main pitch selection component
 * 
 * Refactored UX Flow:
 * 1. PitchSelector appears DISABLED until a zone is selected
 * 2. On zone selection, PitchSelector appears as modal overlay on the strike zone
 * 3. Click outside the modal or select a pitch to close/confirm
 * 4. IBB (Intentional Base on Balls) always selectable with no zone required
 * 
 * Modes:
 * - PITCHER: Select zone → Select pitch type from modal overlay
 * - BATTER: Shows only strike zone grid for swing prediction
 * 
 * @component
 */

import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
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
  // ⭐ NUEVO: Estado para mostrar/ocultar modal de pitch selector
  const [showPitchModal, setShowPitchModal] = useState(false);

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

  /**
   * Handle zone selection: show pitch modal
   */
  const handleZoneSelect = (zone: number) => {
    onSelectZone(zone);
    setShowPitchModal(true);
  };

  /**
   * Handle pitch selection: close modal and confirm selection
   */
  const handlePitchSelect = (pitch: string) => {
    onSelectPitch(pitch);
    setShowPitchModal(false);
  };

  /**
   * Close pitch modal when clicking outside
   */
  const handleModalBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      setShowPitchModal(false);
    }
  };

  return (
    <div
      className={`z-10 flex flex-col items-center gap-3 my-auto transition-opacity relative ${
        disabled ? 'opacity-40 pointer-events-none' : ''
      }`}
    >
      {/* PITCH SELECTOR - Always visible but DISABLED until zone selected */}
      {role === 'PITCHER' && (
        <div
          className={`transition-all duration-300 ${
            showPitchModal ? 'opacity-0 pointer-events-none h-0' : 'opacity-100'
          }`}
        >
          <PitchSelector
            availablePitches={availablePitches}
            selectedPitch={selectedPitch}
            onSelectPitch={onSelectPitch}
            disabled={!showPitchModal && !isIBBMode}  // Disabled until zone selected or IBB active
          />
        </div>
      )}

      {/* STRIKE ZONE GRID - Disabled only if IBB mode (no zone for intentional walk) */}
      <div className="relative">
        <StrikeZoneGrid
          selectedZone={selectedZone}
          onSelectZone={role === 'PITCHER' ? handleZoneSelect : onSelectZone}
          disabled={disabled || isIBBMode}
        />

        {/* PITCH SELECTOR MODAL - Appears over strike zone after selection */}
        {role === 'PITCHER' && showPitchModal && !disabled && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
              onClick={handleModalBackdropClick}
            />

            {/* Modal */}
            <motion.div
              className="absolute inset-0 z-50 flex items-center justify-center p-4"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
            >
              <div className="bg-gradient-to-b from-[#0A0D0F] to-[#121619] border-2 border-[#C5A059] rounded-lg shadow-2xl p-6 max-w-md w-full">
                {/* Modal Header */}
                <div className="mb-4 pb-3 border-b border-[#C5A059]/50">
                  <h3 className="text-center font-mono text-sm font-bold text-[#C5A059] uppercase tracking-wider">
                    ⚾ Select Pitch Type
                  </h3>
                  <p className="text-center font-mono text-[10px] text-[#E6DFD3]/70 mt-1">
                    Zone: {selectedZone}
                  </p>
                </div>

                {/* Pitch Options */}
                <div className="flex flex-wrap justify-center gap-2.5 mb-4">
                  {/* Regular Pitches */}
                  {availablePitches.map((pitch: string) => {
                    const isPitchSelected = selectedPitch === pitch;

                    return (
                      <motion.button
                        key={pitch}
                        type="button"
                        onClick={() => handlePitchSelect(pitch)}
                        className={`relative px-4 py-3 font-mono text-xs uppercase font-bold cursor-pointer rounded-lg overflow-hidden transition-all transform ${
                          isPitchSelected
                            ? 'bg-[#1A3323] text-[#C5A059] border-2 border-[#C5A059] scale-105'
                            : 'bg-[#121619] text-[#E6DFD3] border-2 border-[#2C3E35] hover:border-[#C5A059]/60 hover:scale-105'
                        }`}
                        whileHover={{ scale: 1.08 }}
                        whileTap={{ scale: 0.96 }}
                        animate={
                          isPitchSelected
                            ? {
                                boxShadow: [
                                  '0 0 12px rgba(197, 160, 89, 0.5)',
                                  '0 0 24px rgba(197, 160, 89, 0.9)',
                                  '0 0 12px rgba(197, 160, 89, 0.5)',
                                ],
                              }
                            : { boxShadow: '0 0 0px rgba(0,0,0,0)' }
                        }
                        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                      >
                        <span className="relative z-10">{pitch}</span>
                      </motion.button>
                    );
                  })}

                  {/* IBB (Intentional Walk) Button */}
                  <motion.button
                    type="button"
                    onClick={() => handlePitchSelect('IBB')}
                    className={`relative px-4 py-3 font-mono text-xs uppercase font-bold cursor-pointer rounded-lg overflow-hidden transition-all transform ${
                      selectedPitch === 'IBB'
                        ? 'bg-[#C5A059] text-[#121619] border-2 border-[#F7F5F0] scale-105'
                        : 'bg-[#121619] text-[#C5A059] border-2 border-[#C5A059]/50 hover:border-[#C5A059] hover:scale-105'
                    }`}
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.96 }}
                    animate={
                      selectedPitch === 'IBB'
                        ? {
                            boxShadow: [
                              '0 0 12px rgba(197, 160, 89, 0.6)',
                              '0 0 24px rgba(247, 245, 240, 0.9)',
                              '0 0 12px rgba(197, 160, 89, 0.6)',
                            ],
                          }
                        : { boxShadow: '0 0 0px rgba(0,0,0,0)' }
                    }
                    transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    <span className="relative z-10">🏃 IBB</span>
                  </motion.button>
                </div>

                {/* Modal Footer */}
                <div className="pt-3 border-t border-[#C5A059]/50 text-center">
                  <p className="font-mono text-[9px] text-[#E6DFD3]/60">
                    Click outside to change zone
                  </p>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </div>

      {/* IBB Mode Indicator */}
      {isIBBMode && (
        <div className="text-center px-3 py-2 bg-[#C5A059]/10 border border-[#C5A059]/30 rounded-xs">
          <span className="font-mono text-[9px] text-[#C5A059] uppercase font-bold">
            🏃 Intentional Walk - Ready
          </span>
        </div>
      )}
    </div>
  );
};

PitchZoneGrid.displayName = 'PitchZoneGrid';
