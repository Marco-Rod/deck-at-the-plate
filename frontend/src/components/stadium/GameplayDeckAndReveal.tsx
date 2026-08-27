import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface GameplayDeckAndRevealProps {
  activePlayer: any;
  role: 'PITCHER' | 'BATTER';
  lineupCount?: number;
  triggerKey: string | number; // Cambia cada vez que inicia un nuevo turno para repetir la animación
}

export const GameplayDeckAndReveal: React.FC<GameplayDeckAndRevealProps> = ({
  activePlayer,
  role,
  lineupCount = 5,
  triggerKey,
}) => {
  const [isRevealing, setIsRevealing] = useState(false);

  // Cada vez que cambia el turno (triggerKey), disparamos el zoom y giro cinematográfico
  useEffect(() => {
    setIsRevealing(true);
    const timer = setTimeout(() => {
      setIsRevealing(false);
    }, 1800); // Duración exacta de la animación de revelación

    return () => clearTimeout(timer);
  }, [triggerKey]);

  return (
    <div className="absolute bottom-4 left-6 z-30 flex items-end gap-4 pointer-events-none">
      {/* 1. EFECTO DE MAZO APILADO (STACK DE CARTAS) */}
      <div className="relative w-24 h-36 flex items-center justify-center">
        {Array.from({ length: Math.min(lineupCount, 4) }).map((_, index) => (
          <motion.div
            key={index}
            className="absolute w-20 h-30 bg-[#0A0D0F] border border-[#C5A059]/60 rounded-xs shadow-xl flex flex-col items-center justify-between p-1.5"
            style={{ transformOrigin: 'bottom center' }}
            animate={{
              y: index * -3,
              x: index * 2,
              rotate: index * 3,
            }}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
          >
            <span className="font-mono text-[8px] text-[#C5A059]">MAZO</span>
            <span className="font-sports text-xs text-white">⚾</span>
            <span className="font-mono text-[8px] text-gray-500">#{index + 1}</span>
          </motion.div>
        ))}
      </div>

      {/* 2. EFECTO CINEMATOGRÁFICO DE ZOOM Y GIRO 3D AL INICIAR TURNO */}
      <AnimatePresence>
        {isRevealing && activePlayer && (
          <motion.div
            className="absolute left-32 bottom-0 z-50 bg-[#0A0D0F] border-2 border-[#C5A059] p-4 w-72 shadow-[0_0_50px_rgba(197,160,89,0.7)] rounded-sm"
            style={{ perspective: 1000 }}
            initial={{ scale: 0.4, y: 100, rotateY: 0, opacity: 0 }}
            animate={{
              scale: [0.4, 1.3, 1.1],
              y: [100, -60, 0],
              rotateY: [0, 180, 360], // Giro de 360° en el aire
              opacity: [0, 1, 1],
            }}
            exit={{ opacity: 0, scale: 0.8, y: 50 }}
            transition={{
              duration: 1.6,
              times: [0, 0.6, 1],
              ease: 'easeInOut',
            }}
          >
            <div className="flex justify-between items-center border-b border-[#2C3E35] pb-1 mb-2">
              <span className="font-mono text-xs text-[#C5A059] font-bold tracking-widest">
                ✨ TURNO DE {role === 'PITCHER' ? 'LANZADOR' : 'BATEADOR'}
              </span>
              <span className="font-sports text-2xl text-[#F7F5F0]">
                {activePlayer.overall} OVR
              </span>
            </div>

            <div className="relative h-40 w-full bg-[#121619] border border-[#2C3E35] overflow-hidden mb-2">
              <img
                src={activePlayer.photo}
                alt={activePlayer.name}
                className="w-full h-full object-cover object-top"
              />
              <span className="absolute bottom-1 left-2 font-sports text-2xl text-[#C5A059]">
                #{activePlayer.number}
              </span>
            </div>

            <h3 className="font-sports text-2xl text-white truncate text-center uppercase tracking-wide">
              {activePlayer.name}
            </h3>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};