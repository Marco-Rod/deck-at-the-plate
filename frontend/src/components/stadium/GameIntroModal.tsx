import React, { useState } from 'react';
import { motion } from 'framer-motion';
import playbalBg from '../../assets/playbal.jpg';

interface GameIntroModalProps {
  userTeamName: string;
  userTeamLogo?: string;
  userPitcher?: { name: string; number: string; photo?: string; overall?: number; position?: string };
  userLineup?: { name: string; number: string; photo?: string; overall?: number; position?: string }[];
  cpuTeamName: string;
  cpuTeamLogo?: string;
  cpuPitcher?: { name: string; number: string; photo?: string; overall?: number; position?: string };
  cpuLineup?: { name: string; number: string; photo?: string; overall?: number; position?: string }[];
  onPlayBall: () => void;
}

export const GameIntroModal: React.FC<GameIntroModalProps> = ({
  userTeamName,
  userTeamLogo,
  userPitcher,
  userLineup = [],
  cpuTeamName,
  cpuTeamLogo,
  cpuPitcher,
  cpuLineup = [],
  onPlayBall,
}) => {
  const [isVisible, setIsVisible] = useState(true);

  const handlePlayBall = () => {
    setIsVisible(false);
    // Pequeño delay para que la animación de salida termine
    setTimeout(() => onPlayBall(), 300);
  };

  if (!isVisible) return null;

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      style={{
        backgroundImage: `url(${playbalBg})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      {/* Overlay oscuro para mejorar legibilidad */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

      {/* Container Principal */}
      <motion.div
        className="w-full h-screen flex items-center justify-between px-4 py-6 relative z-10"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      >
        {/* LADO IZQUIERDO: Equipo User */}
        <motion.div
          className="flex flex-col items-center justify-start w-1/3 gap-3"
          initial={{ x: -100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          {/* Logo Equipo */}
          {userTeamLogo && (
            <motion.img
              src={userTeamLogo}
              alt={userTeamName}
              className="w-16 h-16 object-contain drop-shadow-lg"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.4, type: 'spring' }}
            />
          )}

          {/* Nombre Equipo */}
          <h3 className="font-sports text-xl text-[#C5A059] uppercase tracking-wider text-center">
            {userTeamName}
          </h3>

          {/* Lanzador Abridor */}
          {userPitcher && (
            <motion.div
              className="w-full bg-[#121619] border border-[#2C3E35] p-3 rounded text-center"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <p className="text-xs text-gray-400 mb-1">LANZADOR</p>
              {userPitcher.photo && (
                <img
                  src={userPitcher.photo}
                  alt={userPitcher.name}
                  className="w-12 h-12 mx-auto mb-1 object-cover rounded-full"
                />
              )}
              <p className="font-bold text-[#F7F5F0] text-sm">{userPitcher.name}</p>
              <div className="flex justify-between items-center px-1 justify-center text-xs mt-1">
                <p className="text-gray-400">#{userPitcher.number}</p>
                {userPitcher.position && (
                  <p className="text-[#C5A059] font-bold mx-1">{userPitcher.position}</p>
                )}
              </div>
              {userPitcher.overall && (
                <p className="text-xs text-[#C5A059] font-bold mt-1">OVR: {userPitcher.overall}</p>
              )}
            </motion.div>
          )}

          {/* Lineup */}
          <motion.div
            className="w-full space-y-1"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2 text-center font-bold">
              LINEUP
            </p>
            {userLineup.slice(0, 9).map((player, idx) => (
              <motion.div
                key={idx}
                className="bg-[#0A0D0F] border border-[#2C3E35] p-1.5 text-center"
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.7 + idx * 0.03 }}
              >
                <p className="font-bold text-[#C5A059] text-xs">
                  {idx + 1}. {player.name}
                </p>
                <div className="flex justify-between items-center px-1 text-xs">
                  <p className="text-gray-400">#{player.number}</p>
                  {player.position && (
                    <p className="text-[#C5A059]">{player.position}</p>
                  )}
                  {player.overall && (
                    <p className="text-[#C5A059] font-bold">{player.overall}</p>
                  )}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>

        {/* CENTRO: VS y Play Ball */}
        <motion.div
          className="flex flex-col items-center justify-center w-1/3 gap-8"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6, type: 'spring' }}
        >
          {/* VS */}
          <motion.div
            className="font-sports text-8xl font-bold text-[#C5A059] drop-shadow-lg"
            animate={{ scale: [1, 1.1, 1], textShadow: ['0 0 20px rgba(197,160,89,0.5)', '0 0 40px rgba(197,160,89,0.8)', '0 0 20px rgba(197,160,89,0.5)'] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            VS
          </motion.div>

          {/* Play Ball Button */}
          <motion.button
            onClick={handlePlayBall}
            className="bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] px-8 py-4 font-sports text-3xl text-[#C5A059] tracking-wider uppercase cursor-pointer transition-all shadow-2xl"
            whileHover={{ scale: 1.05, boxShadow: '0 0 30px rgba(197,160,89,0.6)' }}
            whileTap={{ scale: 0.95 }}
          >
            ⚾ PLAY BALL
          </motion.button>
        </motion.div>

        {/* LADO DERECHO: Equipo CPU */}
        <motion.div
          className="flex flex-col items-center justify-start w-1/3 gap-3"
          initial={{ x: 100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          {/* Logo Equipo */}
          {cpuTeamLogo && (
            <motion.img
              src={cpuTeamLogo}
              alt={cpuTeamName}
              className="w-16 h-16 object-contain drop-shadow-lg"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.4, type: 'spring' }}
            />
          )}

          {/* Nombre Equipo */}
          <h3 className="font-sports text-xl text-[#F7F5F0] uppercase tracking-wider text-center">
            {cpuTeamName}
          </h3>

          {/* Lanzador Abridor */}
          {cpuPitcher && (
            <motion.div
              className="w-full bg-[#121619] border border-[#2C3E35] p-3 rounded text-center"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <p className="text-xs text-gray-400 mb-1">LANZADOR</p>
              {cpuPitcher.photo && (
                <img
                  src={cpuPitcher.photo}
                  alt={cpuPitcher.name}
                  className="w-12 h-12 mx-auto mb-1 object-cover rounded-full"
                />
              )}
              <p className="font-bold text-[#F7F5F0] text-sm">{cpuPitcher.name}</p>
              <div className="flex justify-between items-center px-1 justify-center text-xs mt-1">
                <p className="text-gray-400">#{cpuPitcher.number}</p>
                {cpuPitcher.position && (
                  <p className="text-[#C5A059] font-bold mx-1">{cpuPitcher.position}</p>
                )}
              </div>
              {cpuPitcher.overall && (
                <p className="text-xs text-[#C5A059] font-bold mt-1">OVR: {cpuPitcher.overall}</p>
              )}
            </motion.div>
          )}

          {/* Lineup */}
          <motion.div
            className="w-full space-y-1"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2 text-center font-bold">
              LINEUP
            </p>
            {cpuLineup.slice(0, 9).map((player, idx) => (
              <motion.div
                key={idx}
                className="bg-[#0A0D0F] border border-[#2C3E35] p-1.5 text-center"
                initial={{ x: 20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.7 + idx * 0.03 }}
              >
                <p className="font-bold text-[#F7F5F0] text-xs">
                  {idx + 1}. {player.name}
                </p>
                <div className="flex justify-between items-center px-1 text-xs">
                  <p className="text-gray-400">#{player.number}</p>
                  {player.position && (
                    <p className="text-[#C5A059]">{player.position}</p>
                  )}
                  {player.overall && (
                    <p className="text-[#C5A059] font-bold">{player.overall}</p>
                  )}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
};
