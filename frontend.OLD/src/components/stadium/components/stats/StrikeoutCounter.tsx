/**
 * StrikeoutCounter - Strikeout counter display
 * 
 * Diseño compacto y profesional:
 * - Pitcher name
 * - K SO label with icon
 * - Large counter number
 * 
 * @component
 * @example
 * <StrikeoutCounter
 *   strikeouts={5}
 *   pitcherName="David Bednar"
 *   animate={true}
 * />
 */

import React from 'react';
import { motion } from 'framer-motion';

interface StrikeoutCounterProps {
  strikeouts: number;
  pitcherName: string;
  animate?: boolean;
}

export const StrikeoutCounter: React.FC<StrikeoutCounterProps> = ({
  strikeouts = 0,
  pitcherName = 'Pitcher',
  animate = false,
}) => {
  return (
    <div className="bg-[#0A0D0F]/95 border border-[#C5A059]/30 rounded-sm p-4 text-center h-full flex flex-col justify-between">
      
      {/* PITCHER NAME */}
      <div className="text-[#F7F5F0] font-mono text-sm font-bold mb-4">
        {pitcherName}
      </div>

      {/* SO LABEL */}
      <div className="text-[#C5A059] text-[11px] font-mono font-bold tracking-widest mb-3">
        K SO
      </div>

      {/* SO COUNTER */}
      <div className="flex-1 flex items-center justify-center">
        <motion.div
          className="font-sports text-6xl text-[#FFD700] font-bold"
          animate={animate ? { scale: [1, 1.15, 1] } : {}}
          transition={{ duration: 0.4 }}
        >
          {strikeouts}
        </motion.div>
      </div>
    </div>
  );
};

StrikeoutCounter.displayName = 'StrikeoutCounter';
