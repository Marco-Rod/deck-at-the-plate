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
                  ? 'border-red-600 bg-red-900/30 text-red-400 font-bold z-10 shadow-lg'
                  : 'border-[#2C3E35] text-[#E6DFD3] hover:border-white/40 bg-[#0A0D0F]'
              }`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {/* White pulse effect on hover */}
              <motion.div
                className="absolute inset-0 border-2 border-white/30 pointer-events-none rounded-xs"
                animate={{ opacity: [0.3, 0.8, 0.3], scale: [1, 1.1, 1] }}
                transition={{
                  duration: 1.2,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
                initial={false}
              />

              {/* Flash effect when selected - Red destello */}
              {isSelected && (
                <>
                  {/* Inner glow - Red pulsing */}
                  <motion.div
                    className="absolute inset-0 border-2 border-red-500 pointer-events-none rounded-xs"
                    animate={{
                      boxShadow: [
                        'inset 0 0 8px rgba(239, 68, 68, 0.3), 0 0 12px rgba(239, 68, 68, 0.5)',
                        'inset 0 0 20px rgba(239, 68, 68, 0.8), 0 0 30px rgba(239, 68, 68, 0.9)',
                        'inset 0 0 8px rgba(239, 68, 68, 0.3), 0 0 12px rgba(239, 68, 68, 0.5)',
                      ],
                    }}
                    transition={{
                      duration: 1.5,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  />

                  {/* Outer rotating ring - Red */}
                  <motion.div
                    className="absolute -inset-1 border-2 border-dashed border-red-500/70 pointer-events-none rounded-xs"
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 8,
                      repeat: Infinity,
                      ease: 'linear',
                    }}
                  />

                  {/* Additional flash burst on selection */}
                  <motion.div
                    className="absolute inset-0 border-2 border-red-400 pointer-events-none rounded-xs"
                    initial={{ boxShadow: '0 0 0px rgba(239, 68, 68, 0.8)' }}
                    animate={{
                      boxShadow: [
                        '0 0 2px rgba(239, 68, 68, 0.8)',
                        '0 0 25px rgba(239, 68, 68, 0.9)',
                        '0 0 2px rgba(239, 68, 68, 0.8)',
                      ],
                    }}
                    transition={{
                      duration: 0.6,
                      repeat: Infinity,
                      repeatDelay: 1.5,
                      ease: 'easeOut',
                    }}
                  />
                </>
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
