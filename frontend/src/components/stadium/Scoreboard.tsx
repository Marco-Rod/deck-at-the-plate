import React, { useEffect, useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GameStateWS, PlayerRole } from '../../types/stadium';

interface ScoreboardProps {
  gameState: GameStateWS;
  role: PlayerRole;
  userRole?: 'HOME' | 'AWAY'; // ⭐ NUEVO: posición del usuario (HOME o AWAY)
  homeTeamName?: string;
  awayTeamName?: string; // Ej: "YANKEES (CPU)"
  homeColor?: string;
  awayColor?: string;
  totalInnings?: number; // Total de innings configurados (3, 6 o 9)
  homeHits?: number; // Hits del equipo HOME
  awayHits?: number; // Hits del equipo AWAY
  inningRuns?: Record<string, number>; // ⭐ NUEVO: {"1_true": 2, "1_false": 1, "6_false": 2}
}

/**
 * Componente interno para animar el número de carreras en estilo carrusel deslizante
 */
const AnimatedDigit: React.FC<{ value: number; colorClass: string }> = ({ value, colorClass }) => {
  return (
    <div className="relative inline-flex items-center justify-center overflow-hidden h-[1.1em] w-[0.8em] align-middle">
      <AnimatePresence mode="popLayout">
        <motion.span
          key={value}
          initial={{ y: '100%', opacity: 0 }}
          animate={{ y: '0%', opacity: 1 }}
          exit={{ y: '-100%', opacity: 0 }}
          transition={{ duration: 0.35, ease: 'easeInOut' }}
          className={`absolute flex items-center justify-center ${colorClass}`}
        >
          {value}
        </motion.span>
      </AnimatePresence>
    </div>
  );
};

/**
 * Scoreboard — Marcador tipo MLB tradicional con grid de 9 innings + CHE
 */
export const Scoreboard: React.FC<ScoreboardProps> = ({
  gameState,
  role,
  userRole = 'HOME',
  homeTeamName = 'HOME',
  awayTeamName = 'RIVAL (CPU)',
  homeColor = '#C5A059',
  awayColor = '#F7F5F0',
  totalInnings = 9,
  homeHits = 0,
  awayHits = 0,
  inningRuns = {},
}) => {
  const {
    currentInning = 1,
    isTopInning = true,
    homeScore = 0,
    awayScore = 0,
    balls = 0,
    strikes = 0,
    outs = 0,
    runners = { b1: null, b2: null, b3: null },
  } = gameState || {};

  // ⭐ Helper para obtener carreras de un inning específico
  // El backend envía claves como "1_True" o "1_False" (capitalizadas)
  // Normalizamos la búsqueda para manejar ambos formatos
  const getInningRuns = (inning: number, isTop: boolean): number => {
    if (!inningRuns) return 0;
    
    // Formar las posibles claves
    const lowercase = `${inning}_${String(isTop).toLowerCase()}`;  // "1_true"
    const capitalized = `${inning}_${String(isTop).charAt(0).toUpperCase()}${String(isTop).slice(1)}`; // "1_True"
    
    console.log(`   [INNING_RUN_LOOKUP] inning=${inning}, isTop=${isTop}, looking for: "${lowercase}" or "${capitalized}"`);
    
    // Buscar en ambas formas
    const value = (inningRuns as any)[lowercase] ?? (inningRuns as any)[capitalized];
    console.log(`   [INNING_RUN_LOOKUP] found value: ${value}`);
    return value || 0;
  };

  // Generar array de innings (1-9 o según extrainnings)
  const displayInnings = useMemo(() => {
    const maxDisplay = Math.max(9, currentInning);
    return Array.from({ length: maxDisplay }, (_, i) => i + 1);
  }, [currentInning]);

  // Extraer inning actual en el contexto de innings mostrados
  const displayedCurrentInning = Math.min(currentInning, 9);

  // ⭐ DEBUG
  console.log('🟣 [SCOREBOARD] Score Calculation:');
  console.log('   userRole:', userRole);
  console.log('   homeScore:', homeScore, 'awayScore:', awayScore);
  console.log('   homeHits:', homeHits, 'awayHits:', awayHits);
  console.log('   inningRuns object:', inningRuns);
  console.log('   inningRuns keys:', Object.keys(inningRuns || {}).join(', '));

  // Efecto visual de destello cuando cambia el marcador
  const [homeFlash, setHomeFlash] = useState(false);
  const [awayFlash, setAwayFlash] = useState(false);
  const [homeFire, setHomeFire] = useState(false);
  const [awayFire, setAwayFire] = useState(false);
  const prevHomeScoreRef = useRef(homeScore);
  const prevAwayScoreRef = useRef(awayScore);

  useEffect(() => {
    setHomeFlash(true);
    const t = setTimeout(() => setHomeFlash(false), 600);
    return () => clearTimeout(t);
  }, [homeScore]);

  useEffect(() => {
    setAwayFlash(true);
    const t = setTimeout(() => setAwayFlash(false), 600);
    return () => clearTimeout(t);
  }, [awayScore]);

  // ⭐ Detectar cuando se anota una carrera y activar fuego
  useEffect(() => {
    if (homeScore > prevHomeScoreRef.current) {
      setHomeFire(true);
      const timer = setTimeout(() => setHomeFire(false), 1200);
      prevHomeScoreRef.current = homeScore;
      return () => clearTimeout(timer);
    }
    prevHomeScoreRef.current = homeScore;
  }, [homeScore]);

  useEffect(() => {
    if (awayScore > prevAwayScoreRef.current) {
      setAwayFire(true);
      const timer = setTimeout(() => setAwayFire(false), 1200);
      prevAwayScoreRef.current = awayScore;
      return () => clearTimeout(timer);
    }
    prevAwayScoreRef.current = awayScore;
  }, [awayScore]);

  return (
    <motion.div
      className="w-full bg-[#0A0D0F] py-1 shadow-2xl font-mono rounded-xs overflow-hidden"
      style={{
        borderWidth: '2px',
        borderColor: '#C5A059',
      }}
      animate={{
        boxShadow: [
          '0 0 10px rgba(197, 160, 89, 0.4)',
          '0 0 25px rgba(197, 160, 89, 0.8)',
          '0 0 10px rgba(197, 160, 89, 0.4)',
        ],
      }}
      transition={{
        duration: 2.5,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
    >
      <div className="flex gap-1 px-2">
        {/* TABLA SCOREBOARD - Full width */}
        <div className="flex-1 overflow-hidden">
          <table className="w-full border-collapse text-center text-xs">
            <thead>
              <tr className="border-b-2 border-[#C5A059]/50">
                <th className="w-10 px-0.5 py-1 bg-[#1A1E22] border-r border-[#C5A059]/30">
                  <div className="text-[8px] font-bold text-[#C5A059]">EQ</div>
                </th>
                {displayInnings.slice(0, 9).map((inning) => (
                  <th
                    key={`header-${inning}`}
                    className="w-9 px-0.5 py-1 bg-[#1A1E22] border-r border-[#C5A059]/30"
                  >
                    <div className="text-[9px] font-bold text-[#C5A059]">{inning}</div>
                  </th>
                ))}
                {/* Separador visual entre innings y CHE */}
                <th className="w-1 bg-[#C5A059]/40"></th>
                <th className="w-9 px-0.5 py-1 bg-[#1A1E22] border-r border-[#C5A059]/30">
                  <div className="text-[8px] font-bold text-[#C5A059]">R</div>
                </th>
                <th className="w-9 px-0.5 py-1 bg-[#1A1E22] border-r border-[#C5A059]/30">
                  <div className="text-[8px] font-bold text-[#C5A059]">H</div>
                </th>
                <th className="w-9 px-0.5 py-1 bg-[#1A1E22]">
                  <div className="text-[8px] font-bold text-[#C5A059]">E</div>
                </th>
              </tr>
            </thead>
            <tbody>
              {/* HOME */}
              <tr className="border-b border-[#C5A059]/20 hover:bg-[#1A1E22]/30">
                <td
                  className="w-10 px-0.5 py-2 bg-[#0A0D0F] border-r border-[#C5A059]/20 text-[8px] font-bold"
                  style={{ color: homeColor }}
                >
                  {homeTeamName?.substring(0, 3).toUpperCase()}
                </td>
                {displayInnings.slice(0, 9).map((inning) => (
                  <motion.td
                    key={`home-${inning}`}
                    className="w-9 px-0.5 py-2 bg-[#0A0D0F] border-r border-[#C5A059]/20 text-sm font-bold"
                    style={{
                      color: homeColor,
                      backgroundColor:
                        inning === displayedCurrentInning && isTopInning
                          ? homeColor + '25'
                          : undefined,
                    }}
                  >
                    {getInningRuns(inning, false)}
                  </motion.td>
                ))}
                {/* Separador visual */}
                <td className="w-1 bg-[#C5A059]/30"></td>
                <motion.td
                  className="w-9 px-0.5 py-2 bg-[#0A0D0F] border-r border-[#C5A059]/20 text-sm font-bold relative"
                  style={{ color: homeColor }}
                  animate={homeFlash ? { scale: [1, 1.15, 1] } : {}}
                  transition={{ duration: 0.5 }}
                >
                  {homeScore}
                  {/* Fuego animado cuando se anota */}
                  {homeFire && (
                    <>
                      <motion.div
                        initial={{ scale: 0, opacity: 1, y: 0 }}
                        animate={{ scale: 1.8, opacity: 0, y: -30 }}
                        transition={{ duration: 1.2 }}
                        className="absolute top-1/2 left-1/2 text-2xl"
                        style={{ transform: 'translate(-50%, -50%)' }}
                      >
                        🔥
                      </motion.div>
                      <motion.div
                        initial={{ scale: 0, opacity: 1, y: 0, x: -15 }}
                        animate={{ scale: 1.5, opacity: 0, y: -25, x: -30 }}
                        transition={{ duration: 1.2, delay: 0.1 }}
                        className="absolute top-1/2 left-1/2 text-xl"
                        style={{ transform: 'translate(-50%, -50%)' }}
                      >
                        🔥
                      </motion.div>
                      <motion.div
                        initial={{ scale: 0, opacity: 1, y: 0, x: 15 }}
                        animate={{ scale: 1.5, opacity: 0, y: -25, x: 30 }}
                        transition={{ duration: 1.2, delay: 0.1 }}
                        className="absolute top-1/2 left-1/2 text-xl"
                        style={{ transform: 'translate(-50%, -50%)' }}
                      >
                        🔥
                      </motion.div>
                    </>
                  )}
                </motion.td>
                <td
                  className="w-9 px-0.5 py-2 bg-[#0A0D0F] border-r border-[#C5A059]/20 text-sm font-bold"
                  style={{ color: homeColor }}
                >
                  {homeHits}
                </td>
                <td className="w-9 px-0.5 py-2 bg-[#0A0D0F] text-sm font-bold text-[#C5A059]">
                  0
                </td>
              </tr>
              {/* AWAY */}
              <tr className="hover:bg-[#1A1E22]/30">
                <td
                  className="w-10 px-0.5 py-2 bg-[#0A0D0F] border-r border-[#C5A059]/20 text-[8px] font-bold"
                  style={{ color: awayColor }}
                >
                  {awayTeamName?.substring(0, 3).toUpperCase()}
                </td>
                {displayInnings.slice(0, 9).map((inning) => (
                  <motion.td
                    key={`away-${inning}`}
                    className="w-9 px-0.5 py-2 bg-[#0A0D0F] border-r border-[#C5A059]/20 text-sm font-bold"
                    style={{
                      color: awayColor,
                      backgroundColor:
                        inning === displayedCurrentInning && !isTopInning
                          ? awayColor + '25'
                          : undefined,
                    }}
                  >
                    {getInningRuns(inning, true)}
                  </motion.td>
                ))}
                {/* Separador visual */}
                <td className="w-1 bg-[#C5A059]/30"></td>
                <motion.td
                  className="w-9 px-0.5 py-2 bg-[#0A0D0F] border-r border-[#C5A059]/20 text-sm font-bold relative"
                  style={{ color: awayColor }}
                  animate={awayFlash ? { scale: [1, 1.15, 1] } : {}}
                  transition={{ duration: 0.5 }}
                >
                  {awayScore}
                  {/* Fuego animado cuando se anota */}
                  {awayFire && (
                    <>
                      <motion.div
                        initial={{ scale: 0, opacity: 1, y: 0 }}
                        animate={{ scale: 1.8, opacity: 0, y: -30 }}
                        transition={{ duration: 1.2 }}
                        className="absolute top-1/2 left-1/2 text-2xl"
                        style={{ transform: 'translate(-50%, -50%)' }}
                      >
                        🔥
                      </motion.div>
                      <motion.div
                        initial={{ scale: 0, opacity: 1, y: 0, x: -15 }}
                        animate={{ scale: 1.5, opacity: 0, y: -25, x: -30 }}
                        transition={{ duration: 1.2, delay: 0.1 }}
                        className="absolute top-1/2 left-1/2 text-xl"
                        style={{ transform: 'translate(-50%, -50%)' }}
                      >
                        🔥
                      </motion.div>
                      <motion.div
                        initial={{ scale: 0, opacity: 1, y: 0, x: 15 }}
                        animate={{ scale: 1.5, opacity: 0, y: -25, x: 30 }}
                        transition={{ duration: 1.2, delay: 0.1 }}
                        className="absolute top-1/2 left-1/2 text-xl"
                        style={{ transform: 'translate(-50%, -50%)' }}
                      >
                        🔥
                      </motion.div>
                    </>
                  )}
                </motion.td>
                <td
                  className="w-9 px-0.5 py-2 bg-[#0A0D0F] border-r border-[#C5A059]/20 text-sm font-bold"
                  style={{ color: awayColor }}
                >
                  {awayHits}
                </td>
                <td className="w-9 px-0.5 py-2 bg-[#0A0D0F] text-sm font-bold text-[#C5A059]">
                  0
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
};