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
import { createPortal } from 'react-dom';
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
   * IBB can be selected independently without requiring zone selection
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
    // Simplemente cierra el modal - click en el backdrop exterior
    setShowPitchModal(false);
  };

  return (
    <div
      className={`flex flex-col items-center gap-3 my-auto transition-opacity relative ${
        disabled ? 'opacity-40 pointer-events-none' : ''
      }`}
    >
      {/* STRIKE ZONE GRID - Only disabled by game state, not by IBB */}
      <div className="relative">
        <StrikeZoneGrid
          selectedZone={selectedZone}
          onSelectZone={role === 'PITCHER' ? handleZoneSelect : onSelectZone}
          disabled={disabled}
        />
      </div>

      {/* PITCH SELECTOR MODAL - Rendered via Portal (outside component tree) */}
      {role === 'PITCHER' && showPitchModal && !disabled &&
        createPortal(
          <div
            className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6 lg:p-8"
            onClick={handleModalBackdropClick}
          >
            {/* Backdrop blur effect - covers everything but doesn't capture clicks */}
            <div className="fixed inset-0 z-0 bg-black/40 backdrop-blur-sm pointer-events-none" />

            {/* Modal - Higher z-index to appear above backdrop */}
            <motion.div
              className="relative z-[10000] bg-gradient-to-b from-[#0A0D0F] to-[#121619] border-2 border-[#C5A059] rounded-lg shadow-2xl p-6 sm:p-8 lg:p-10 w-full max-w-2xl max-h-[80vh] overflow-y-auto"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="mb-6 pb-4 border-b border-[#C5A059]/50">
                <h3 className="text-center font-mono text-lg sm:text-xl font-bold text-[#C5A059] uppercase tracking-wider">
                  ⚾ Select Pitch Type
                </h3>
                <p className="text-center font-mono text-xs sm:text-sm text-[#E6DFD3]/70 mt-2">
                  Zone: {selectedZone}
                </p>
              </div>

              {/* Pitch Options - Single horizontal line with plenty of space */}
              <div className="mb-6 flex flex-wrap justify-center gap-3 sm:gap-4">
                {/* Regular Pitches */}
                {availablePitches.map((pitch: string) => {
                  const isPitchSelected = selectedPitch === pitch;

                  return (
                    <motion.button
                      key={pitch}
                      type="button"
                      onClick={() => handlePitchSelect(pitch)}
                      className={`relative px-5 sm:px-6 py-3 sm:py-4 font-mono text-sm sm:text-base uppercase font-bold cursor-pointer rounded-lg overflow-hidden transition-all transform ${
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
                  className={`relative px-5 sm:px-6 py-3 sm:py-4 font-mono text-sm sm:text-base uppercase font-bold cursor-pointer rounded-lg overflow-hidden transition-all transform ${
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
              <div className="pt-4 border-t border-[#C5A059]/50 text-center">
                <p className="font-mono text-xs sm:text-sm text-[#E6DFD3]/60">
                  Click outside to change zone
                </p>
              </div>
            </motion.div>
          </div>,
          document.body
        )}

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
