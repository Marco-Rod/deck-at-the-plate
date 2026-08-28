/**
 * SubmitPlayButton - Main action button for submitting play
 * 
 * Sub-component of TacticalHand (extracted for clarity)
 * Shows animated button with fire effects and particle animation
 * 
 * Features:
 * - Pulsing glow effect
 * - Floating fire particles
 * - Hover vibration animation
 * - Tap feedback
 * - Disabled state
 * 
 * @component
 * @example
 * <SubmitPlayButton
 *   label="LANZAR 🔥"
 *   disabled={false}
 *   onSubmit={() => handlePlay()}
 * />
 */

import React from 'react';
import { motion } from 'framer-motion';

interface SubmitPlayButtonProps {
  label: string;
  disabled?: boolean;
  onSubmit: () => void;
}

export const SubmitPlayButton: React.FC<SubmitPlayButtonProps> = ({
  label,
  disabled = false,
  onSubmit,
}) => {
  return (
    <div className="flex flex-col items-center">
      <motion.button
        type="button"
        onClick={onSubmit}
        disabled={disabled}
        className={`relative bg-[#1A100A] border-2 border-orange-500 px-8 py-3.5 font-sports text-3xl text-[#F7F5F0] tracking-widest shadow-2xl rounded-sm overflow-hidden flex items-center gap-3 ${
          disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
        }`}
        animate={{
          boxShadow: [
            '0 0 15px rgba(239, 68, 68, 0.6), inset 0 0 10px rgba(249, 115, 22, 0.4)',
            '0 0 35px rgba(249, 115, 22, 0.9), inset 0 0 20px rgba(234, 179, 8, 0.7)',
            '0 0 15px rgba(239, 68, 68, 0.6), inset 0 0 10px rgba(249, 115, 22, 0.4)',
          ],
          borderColor: ['#ef4444', '#f97316', '#eab308', '#ef4444'],
          scale: [1, 1.03, 1],
        }}
        transition={{
          duration: 1.8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        whileHover={{
          scale: 1.07,
          backgroundColor: '#381404',
          borderColor: '#f97316',
          rotate: [0, -1, 1, -1, 1, 0],
          transition: {
            rotate: { repeat: Infinity, duration: 0.12 },
            scale: { duration: 0.2 },
          },
        }}
        whileTap={{ scale: 0.95 }}
      >
        {/* Fire Particles */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden flex items-end justify-center">
          {Array.from({ length: 4 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-4 h-8 rounded-full bg-gradient-to-t from-red-600 via-orange-500 to-yellow-400 opacity-60 blur-[1px]"
              initial={{ y: 15, x: (i - 2) * 20, scale: 0.4, opacity: 0 }}
              animate={{
                y: [-5, -35, -50],
                x: [(i - 2) * 20, (i - 2) * 25 + (i % 2 === 0 ? 8 : -8)],
                scale: [0.4, 1, 0.1],
                opacity: [0, 0.7, 0],
              }}
              transition={{
                duration: 1 + (i * 0.2),
                repeat: Infinity,
                ease: 'easeOut',
                delay: i * 0.25,
              }}
            />
          ))}
        </div>

        {/* Internal Light Flash */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-orange-500/30 to-transparent pointer-events-none"
          animate={{ x: ['-100%', '100%'] }}
          transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}
        />

        {/* Button Text */}
        <span className="relative z-10 flex items-center gap-3 text-orange-200 drop-shadow-[0_0_8px_rgba(249,115,22,0.8)]">
          {label}
        </span>
      </motion.button>

      {/* Subtitle */}
      <span className="font-mono text-[9px] text-orange-400 uppercase tracking-wider mt-1 font-bold">
        🔥 CONFIRMA LA JUGADA 🔥
      </span>
    </div>
  );
};

SubmitPlayButton.displayName = 'SubmitPlayButton';
