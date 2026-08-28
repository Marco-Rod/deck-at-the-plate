/**
 * StrikeZoneGrid - 3x3 grid for selecting strike zones
 * 
 * Sub-component of PitchZoneGrid (extracted for clarity)
 * Displays 9 zones with interactive selection and animations
 * 
 * @component
 * @example
 * <StrikeZoneGrid
 *   selectedZone={5}
 *   onSelectZone={(zone) => setSelectedZone(zone)}
 *   disabled={false}
 * />
 */

import React from 'react';
import { motion } from 'framer-motion';

interface StrikeZoneGridProps {
  selectedZone: number;
  onSelectZone: (zone: number) => void;
  disabled?: boolean;
}

const STRIKE_ZONES = [1, 2, 3, 4, 5, 6, 7, 8, 9];

export const StrikeZoneGrid: React.FC<StrikeZoneGridProps> = ({
  selectedZone,
  onSelectZone,
  disabled = false,
}) => {
  return (
    <div
      className={`bg-[#0A0D0F]/95 p-4 border-2 border-[#C5A059] shadow-2xl text-center transition-all ${
        disabled ? 'opacity-40 pointer-events-none' : ''
      }`}
    >
      {/* Header */}
      <div className="mb-3 pb-2 border-b border-[#C5A059]/30">
        <span className="font-mono text-[10px] text-[#C5A059] uppercase block font-bold">
          STRIKE ZONE
        </span>
      </div>

      {/* Grid 3x3 */}
      <div className="grid grid-cols-3 gap-2">
        {STRIKE_ZONES.map((zone: number) => {
          const isSelected = selectedZone === zone;

          return (
            <motion.button
              key={zone}
              type="button"
              onClick={() => onSelectZone(zone)}
              className={`relative w-16 h-16 border flex items-center justify-center font-mono text-xs cursor-pointer overflow-hidden transition-all ${
                isSelected
                  ? 'border-[#C5A059] bg-[#1A3323] text-[#C5A059] font-bold z-10'
                  : 'border-[#2C3E35] text-[#E6DFD3] hover:border-[#C5A059]/60 bg-[#0A0D0F]'
              }`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {/* Glow effect when selected */}
              {isSelected && (
                <motion.div
                  className="absolute inset-0 border-2 border-[#C5A059] pointer-events-none"
                  animate={{
                    boxShadow: [
                      'inset 0 0 5px rgba(197, 160, 89, 0.4), 0 0 5px rgba(197, 160, 89, 0.4)',
                      'inset 0 0 15px rgba(197, 160, 89, 0.9), 0 0 20px rgba(197, 160, 89, 0.8)',
                      'inset 0 0 5px rgba(197, 160, 89, 0.4), 0 0 5px rgba(197, 160, 89, 0.4)',
                    ],
                  }}
                  transition={{
                    duration: 1.8,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                />
              )}

              {/* Rotating ring when selected */}
              {isSelected && (
                <motion.div
                  className="absolute inset-1 border border-dashed border-[#C5A059]/70 pointer-events-none rounded-xs"
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 10,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                />
              )}

              {/* Zone Label */}
              <span className="relative z-10 font-bold">Z{zone}</span>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
};

StrikeZoneGrid.displayName = 'StrikeZoneGrid';
