/**
 * PitchSelector - Buttons for selecting pitch type
 * 
 * Sub-component of PitchZoneGrid (extracted for clarity)
 * Displays available pitches + IBB option with animations
 * 
 * @component
 * @example
 * <PitchSelector
 *   availablePitches={['4-SEAM', 'SLIDER']}
 *   selectedPitch="4-SEAM"
 *   onSelectPitch={(pitch) => setSelectedPitch(pitch)}
 *   disabled={false}
 * />
 */

import React from 'react';
import { motion } from 'framer-motion';

interface PitchSelectorProps {
  availablePitches: string[];
  selectedPitch: string;
  onSelectPitch: (pitch: string) => void;
  disabled?: boolean;
}

export const PitchSelector: React.FC<PitchSelectorProps> = ({
  availablePitches,
  selectedPitch,
  onSelectPitch,
  disabled = false,
}) => {
  return (
    <div className={`flex flex-wrap justify-center gap-1.5 bg-[#0A0D0F] p-1.5 border border-[#C5A059]/40 rounded-xs shadow-xl ${disabled ? 'opacity-50 pointer-events-none' : ''}`}>
      {/* Regular Pitches */}
      {availablePitches.map((pitch: string) => {
        const isPitchSelected = selectedPitch === pitch;
        
        return (
          <motion.button
            key={pitch}
            type="button"
            onClick={() => onSelectPitch(pitch)}
            className={`relative px-3 py-1.5 font-mono text-[10px] uppercase cursor-pointer rounded-xs overflow-hidden transition-all ${
              isPitchSelected
                ? 'bg-[#1A3323] text-[#C5A059] border border-[#C5A059] font-bold z-10'
                : 'bg-[#0A0D0F] text-[#E6DFD3] border border-[#2C3E35] opacity-70 hover:opacity-100'
            }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            animate={
              isPitchSelected
                ? {
                    boxShadow: [
                      '0 0 8px rgba(197, 160, 89, 0.4)',
                      '0 0 16px rgba(197, 160, 89, 0.8)',
                      '0 0 8px rgba(197, 160, 89, 0.4)',
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
        onClick={() => onSelectPitch('IBB')}
        className={`relative px-2.5 py-1.5 font-mono text-[10px] uppercase cursor-pointer rounded-xs overflow-hidden transition-all ${
          selectedPitch === 'IBB'
            ? 'bg-[#C5A059] text-[#121619] font-bold border border-[#F7F5F0] z-10'
            : 'bg-[#0A0D0F] text-[#C5A059] border border-[#C5A059]/40 opacity-80 hover:opacity-100'
        }`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        animate={
          selectedPitch === 'IBB'
            ? {
                boxShadow: [
                  '0 0 8px rgba(197, 160, 89, 0.5)',
                  '0 0 18px rgba(247, 245, 240, 0.9)',
                  '0 0 8px rgba(197, 160, 89, 0.5)',
                ],
              }
            : { boxShadow: '0 0 0px rgba(0,0,0,0)' }
        }
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
      >
        <span className="relative z-10">IBB (INTENC.)</span>
      </motion.button>
    </div>
  );
};

PitchSelector.displayName = 'PitchSelector';
