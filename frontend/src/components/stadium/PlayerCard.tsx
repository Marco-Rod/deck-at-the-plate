import React from 'react';
import { motion } from 'framer-motion';
import { PlayerData, PlayerRole } from '../../types/stadium';
import RHPitcherSvg from '../../assets/silhouettes/rhpitcher.svg';
import RHbatterSvg from '../../assets/silhouettes/rhbatter.svg';

interface PlayerCardProps {
  player: PlayerData | null;
  role: PlayerRole;
}

// Configuración de colores según la rareza basada en el Overall
const getRarityConfig = (overall: number = 75) => {
  if (overall >= 90) {
    return { borderColor: '#C5A059', shadowColor: 'rgba(197, 160, 89, 0.8)' }; // Diamante (Dorado)
  } else if (overall >= 85) {
    return { borderColor: '#EAB308', shadowColor: 'rgba(234, 179, 8, 0.7)' };  // Oro (Ámbar)
  } else if (overall >= 80) {
    return { borderColor: '#94A3B8', shadowColor: 'rgba(148, 163, 184, 0.6)' }; // Plata (Metálico)
  }
  return { borderColor: '#B45309', shadowColor: 'rgba(180, 83, 9, 0.5)' };    // Bronce
};

export const PlayerCard: React.FC<PlayerCardProps> = ({ player, role }) => {
  if (!player) {
    return (
      <div className="z-10 bg-[#0A0D0F]/90 border border-[#C5A059] p-3 w-60 shadow-2xl flex flex-col items-center justify-center min-h-[300px]">
        <span className="font-mono text-xs text-[#C5A059] animate-pulse">
          CARGANDO {role === 'PITCHER' ? 'LANZADOR' : 'BATEADOR'}...
        </span>
      </div>
    );
  }

  const rarity = getRarityConfig(player.overall);

  return (
    <motion.div
      className="relative z-10 bg-[#0A0D0F]/90 p-3 w-60 backdrop-blur-sm rounded-xs cursor-pointer select-none"
      style={{
        borderWidth: '2px',
        borderColor: rarity.borderColor,
      }}
      // 1. Pulso luminoso constante en reposo
      animate={{
        boxShadow: [
          `0 0 10px ${rarity.shadowColor}`,
          `0 0 25px ${rarity.shadowColor}`,
          `0 0 10px ${rarity.shadowColor}`,
        ],
      }}
      transition={{
        duration: 2.5,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
      // 2. Efecto al pasar el cursor (Hover con vibración y elevación)
      whileHover={{
        scale: 1.05,
        y: -6,
        rotate: [0, -1, 1, -1, 1, 0], // Vibración sutil horizontal
        transition: {
          rotate: { repeat: Infinity, duration: 0.15 },
          scale: { duration: 0.2 },
          y: { duration: 0.2 },
        },
      }}
      // 3. Feedback táctil al hacer clic
      whileTap={{ scale: 0.97 }}
    >
      <div className="flex justify-between items-center border-b border-[#2C3E35] pb-1 mb-2">
        <span className="font-mono text-[10px] text-[#C5A059] font-bold">
          {role === 'PITCHER' ? 'LANZADOR' : 'BATEADOR'}
        </span>
        <span className="font-sports text-xl text-[#F7F5F0]">
          {player?.overall ?? '--'}
        </span>
      </div>

      {/* Contenedor de la ilustración con zoom enfocado en el torso */}
      <div className="relative h-44 w-full bg-[#121619] border border-[#2C3E35] overflow-hidden mb-2 flex items-center justify-center">
        <div className="w-48 h-48 opacity-90 drop-shadow-[0_0_12px_rgba(197,160,89,0.4)] flex items-center justify-center">
          <img
            src={role === 'PITCHer' || role === 'PITCHER' ? RHPitcherSvg : RHbatterSvg}
            alt={role === 'PITCHER' ? 'Silueta Lanzador' : 'Silueta Bateador'}
            className="w-full h-full object-contain filter brightness-0 saturate-100 invert-[75%] sepia-[48%] saturate-[412%] hue-rotate-[5deg] scale-160 -translate-y-4 pointer-events-none"
          />
        </div>

        <span className="absolute bottom-1 left-2 font-sports text-2xl text-[#C5A059] drop-shadow-md">
          #{player?.number || '0'}
        </span>
        <span className="absolute bottom-1 right-2 font-mono text-[10px] text-[#E6DFD3]">
          {player?.position || '--'}
        </span>
      </div>

      <h4 className="font-sports text-xl text-[#F7F5F0] leading-none mb-1 truncate">
        {player?.name || 'Cargando...'}
      </h4>

      <div className="space-y-1.5 font-mono text-[9px] mt-2">
        <span className="text-[#C5A059] font-bold block mb-1">ESTADÍSTICAS</span>
        {player?.stats?.map((s) => (
          <div key={s.label} className="flex items-center justify-between gap-2">
            <span className="w-6 text-[#E6DFD3]">{s.label}</span>
            <div className="flex-1 h-1.5 bg-[#121619] border border-[#2C3E35]">
              <div
                className="h-full bg-[#C5A059]"
                style={{ width: `${Math.min(s.val, 100)}%` }}
              />
            </div>
            <span className="w-5 text-right">{s.val}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
};