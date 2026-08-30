import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface InningTransitionModalProps {
  completedInning: number;
  completedHalf: 'TOP' | 'BOT';
  nextInning: number;
  nextHalf: 'TOP' | 'BOT';
  homeScore: number;
  awayScore: number;
  userRole?: 'HOME' | 'AWAY'; // ⭐ NUEVO: posición del usuario
}

export const InningTransitionModal: React.FC<InningTransitionModalProps> = ({
  completedInning,
  completedHalf,
  nextInning,
  nextHalf,
  homeScore,
  awayScore,
  userRole = 'HOME', // ⭐ NUEVO: por defecto HOME
}) => {
  // ⭐ ARREGLADO: Intercambiar scores según userRole
  const userScore = userRole === 'HOME' ? homeScore : awayScore;
  const cpuScore = userRole === 'HOME' ? awayScore : homeScore;
  const [progress, setProgress] = useState(0);

  // Barra de progreso lineal durante 3 segundos
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 1.67, 100)); // 100/60 ≈ 1.67 por frame @ 60fps durante 3s
    }, 16); // 16ms ≈ 60fps

    return () => clearInterval(interval);
  }, []);

  const halfLabel = completedHalf === 'TOP' ? 'ALTA' : 'BAJA';
  const nextHalfLabel = nextHalf === 'TOP' ? 'ALTA' : 'BAJA';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md">
      {/* Container Principal */}
      <motion.div
        className="bg-[#0A0D0F] border-2 border-[#C5A059] p-8 max-w-md w-full shadow-[0_0_50px_rgba(197,160,89,0.4)]"
        initial={{ opacity: 0, scale: 0.8, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.8, y: -20 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      >
        {/* Header */}
        <div className="text-center font-mono mb-6">
          <span className="text-xs text-[#C5A059] font-bold tracking-widest uppercase block mb-2">
            FIN DE ENTRADA • INNING COMPLETE
          </span>
          <h2 className="font-sports text-3xl text-[#F7F5F0] uppercase tracking-wider">
            3 OUTS
          </h2>
        </div>

        {/* Entrada Completada */}
        <motion.div
          className="bg-[#121619] border border-[#2C3E35] p-4 mb-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.3 }}
        >
          <p className="text-xs text-gray-400 text-center mb-2">ENTRADA COMPLETADA</p>
          <p className="font-sports text-2xl text-[#C5A059] text-center">
            {completedInning}ª {halfLabel}
          </p>
        </motion.div>

        {/* Marcador Parcial */}
        <motion.div
          className="bg-[#121619] border border-[#2C3E35] p-4 mb-4 flex justify-around items-center"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.3 }}
        >
          <div className="flex flex-col items-center">
            <span className="text-xs text-gray-400 mb-1">{userRole === 'HOME' ? 'HOME' : 'VISITOR'}</span>
            <span className="font-sports text-2xl text-[#C5A059]">{userScore}</span>
          </div>
          <span className="font-sports text-xl text-gray-600">-</span>
          <div className="flex flex-col items-center">
            <span className="text-xs text-gray-400 mb-1">{userRole === 'HOME' ? 'VISITOR' : 'HOME'}</span>
            <span className="font-sports text-2xl text-[#F7F5F0]">{cpuScore}</span>
          </div>
        </motion.div>

        {/* Siguiente Media Entrada */}
        <motion.div
          className="bg-[#1A3323] border border-[#4D7A5C] p-4 mb-6"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.3 }}
        >
          <p className="text-xs text-[#7FBE9F] text-center mb-2">SIGUIENTE ENTRADA</p>
          <p className="font-sports text-xl text-[#7FBE9F] text-center uppercase">
            {nextInning}ª {nextHalfLabel}
          </p>
        </motion.div>

        {/* Barra de Progreso */}
        <div className="bg-[#0A0D0F] border border-[#2C3E35] h-2 overflow-hidden rounded-sm">
          <motion.div
            className="bg-gradient-to-r from-[#C5A059] to-[#7FBE9F] h-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.05, ease: 'linear' }}
          />
        </div>
      </motion.div>
    </div>
  );
};
