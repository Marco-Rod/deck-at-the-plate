import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface PlayerStat {
  name: string;
  number: string;
  at_bats: number;
  hits: number;
  doubles: number;
  triples: number;
  home_runs: number;
  rbi: number;
  runs: number;
  strikeouts: number;
  walks: number;
  position?: string;
}

interface GameStatsPanelProps {
  lineup: Array<{
    name: string;
    number: string;
    photo?: string;
    overall?: number;
    position?: string;
    id?: string; // ID de la tarjeta del jugador
  }>;
  stats: Record<string, any>; // {player_id: {hits, at_bats, ...}}
  isPitcher: boolean; // True si mostrar stats del pitcher
  pitcherStrikeouts?: number; // SO del pitcher
  pitcherName?: string; // ⭐ NUEVO: nombre del pitcher
  animateStrikeout?: boolean; // Trigger animación de strikeout
}

export const GameStatsPanel: React.FC<GameStatsPanelProps> = ({
  lineup,
  stats,
  isPitcher,
  pitcherStrikeouts = 0,
  pitcherName = "Pitcher", // ⭐ NUEVO
  animateStrikeout = false,
}) => {
  const [animatingPitcher, setAnimatingPitcher] = useState(false);

  // Trigger animación cuando strikeout
  useEffect(() => {
    if (animateStrikeout) {
      setAnimatingPitcher(true);
      const timer = setTimeout(() => setAnimatingPitcher(false), 600);
      return () => clearTimeout(timer);
    }
  }, [animateStrikeout]);

  // Formatear línea de stats para un bateador (ej: "2-4 2B, HR, 2RBI 1R")
  const formatBatterLine = (playerStats: any): string => {
    if (!playerStats) return '0-0';
    const { at_bats = 0, hits = 0, doubles = 0, triples = 0, home_runs = 0, rbi = 0, runs = 0, strikeouts = 0, walks = 0 } = playerStats;
    
    // Si solo hay walks (sin at-bats), mostrar solo los walks
    if (at_bats === 0 && walks > 0) {
      const walkLine = `0-0 ${walks}BB`;
      const extraStats = [];
      if (rbi > 0) extraStats.push(`${rbi}RBI`);
      if (runs > 0) extraStats.push(`${runs}R`);
      return `${walkLine}${extraStats.length > 0 ? ' ' + extraStats.join(' ') : ''}`;
    }
    
    const line = `${hits}-${at_bats}`;
    const details = [];
    
    if (doubles > 0) details.push(`${doubles}2B`);
    if (triples > 0) details.push(`${triples}3B`);
    if (home_runs > 0) details.push(`${home_runs}HR`);
    if (strikeouts > 0) details.push(`${strikeouts}SO`);
    if (walks > 0) details.push(`${walks}BB`);
    
    const extraStats = [];
    if (rbi > 0) extraStats.push(`${rbi}RBI`);
    if (runs > 0) extraStats.push(`${runs}R`);
    
    return `${line}${details.length > 0 ? ' ' + details.join(', ') : ''}${extraStats.length > 0 ? ' ' + extraStats.join(' ') : ''}`;
  };

  if (isPitcher) {
    // Mostrar solo stats del pitcher activo con animación de strikeout
    return (
      <div className="flex flex-col items-center justify-center gap-2">
        <div className="text-xs text-[#C5A059] mb-1">{pitcherName}</div>
        <motion.div
          animate={animatingPitcher ? { scale: [1, 1.5, 1] } : {}}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <div className="text-xs text-gray-400 mb-1">🔥 SO</div>
          <div className="text-3xl font-bold text-[#C5A059]">
            {pitcherStrikeouts}
          </div>
        </motion.div>
        
        {animatingPitcher && (
          <motion.div
            initial={{ scale: 0, opacity: 1 }}
            animate={{ scale: 1.5, opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="absolute text-4xl"
          >
            🔥
          </motion.div>
        )}
      </div>
    );
  }

  // Mostrar lineup con estadísticas (máx 9 bateadores)
  return (
    <div className="flex flex-col gap-1.5 max-h-[450px] overflow-y-auto pr-2">
      {lineup.slice(0, 9).map((player, idx) => {
        const playerStats = stats?.[player.id || player.number] || {};
        const statLine = formatBatterLine(playerStats);
        
        if (idx === 0) {
          console.log('⭐ [GAMESTATS_PANEL] First player lookup:', {
            player_id: player.id,
            player_number: player.number,
            stats_keys: Object.keys(stats || {}),
            found_stats: playerStats,
          });
        }
        
        return (
          <motion.div
            key={`${player.id || player.number}-${idx}`}
            className="flex items-center gap-2 px-2 py-1 bg-[#1A1E22]/80 border border-[#C5A059]/20 rounded text-xs hover:border-[#C5A059]/50 transition-colors"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            whileHover={{ backgroundColor: '#1A1E22' }}
          >
            <span className="font-bold text-[#C5A059] w-5 text-center">{idx + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="font-sports text-[#F7F5F0] truncate text-xs">{player.name}</div>
              <div className="text-[9px] text-gray-500">#{player.number}</div>
            </div>
            <div className="text-right">
              <div className="font-mono text-[#C5A059] font-bold text-xs">{statLine}</div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};
