/**
 * PitcherStaminaBar - Pitcher fatigue/stamina visualization component
 * 
 * Propósito:
 * Mostrar en tiempo real la fatiga del lanzador con:
 * - Barra de stamina con degradación de color por porcentaje
 * - Estadísticas de fatiga (velocidad, control, movimiento) con penalizaciones
 * - Contador de lanzamientos realizados
 * - Indicador de umbral de fatiga
 * 
 * Colores de degradación:
 * - 0-40%: Verde (sin fatiga / poco)
 * - 40-70%: Amarillo (moderadamente fatigado)
 * - 70-85%: Naranja (muy fatigado)
 * - 85-100%: Rojo (crítico)
 * 
 * Responsivo:
 * - sm: Mobile (texto pequeño, barra compacta)
 * - md: Tablet (intermedio)
 * - lg: Desktop (full size)
 * 
 * @component
 * @example
 * <PitcherStaminaBar
 *   pitchCount={75}
 *   fatigueLevel={35.2}
 *   basePitcherStats={{ velocidad: 95, control: 88, movimiento: 82 }}
 * />
 */

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

interface PitcherStaminaBarProps {
  pitchCount?: number;
  fatigueLevel?: number;
  basePitcherStats?: {
    velocidad?: number;
    control?: number;
    movimiento?: number;
  };
}

interface FatigueStats {
  velocidad: number;
  control: number;
  movimiento: number;
}

/**
 * Calcula la penalización de fatiga basada en el porcentaje
 * Usa la fórmula del backend: -3% por cada tramo de 15 lanzamientos extra
 */
const calculateFatigueStats = (
  baseStats: { velocidad?: number; control?: number; movimiento?: number },
  pitchCount: number = 0
): FatigueStats => {
  const PITCH_THRESHOLD = 60;
  const FATIGUE_PENALTY_STEP = 15;

  const base = {
    velocidad: baseStats.velocidad || 75,
    control: baseStats.control || 75,
    movimiento: baseStats.movimiento || 75,
  };

  if (pitchCount <= PITCH_THRESHOLD) {
    return base;
  }

  const extraPitches = pitchCount - PITCH_THRESHOLD;
  const penalty = Math.max(
    0.5, // Mínimo 50% de stats
    1.0 - 0.03 * (Math.floor(extraPitches / FATIGUE_PENALTY_STEP) + 1)
  );

  return {
    velocidad: Math.round(base.velocidad * penalty),
    control: Math.round(base.control * penalty),
    movimiento: Math.round(base.movimiento * penalty),
  };
};

/**
 * Obtiene el color y etiqueta basado en el nivel de fatiga
 */
const getStaminaColor = (fatigueLevel: number): { color: string; label: string; bgColor: string } => {
  if (fatigueLevel < 40) {
    return {
      color: '#22C55E', // Verde
      label: 'Fresco',
      bgColor: '#0F766E',
    };
  }
  if (fatigueLevel < 70) {
    return {
      color: '#EAB308', // Amarillo
      label: 'Moderado',
      bgColor: '#713F12',
    };
  }
  if (fatigueLevel < 85) {
    return {
      color: '#F97316', // Naranja
      label: 'Muy Cansado',
      bgColor: '#7C2D12',
    };
  }
  return {
    color: '#EF4444', // Rojo
    label: 'Crítico',
    bgColor: '#7F1D1D',
  };
};

export const PitcherStaminaBar: React.FC<PitcherStaminaBarProps> = ({
  pitchCount = 0,
  fatigueLevel = 0,
  basePitcherStats = {},
}) => {
  // Calcular stats con penalización de fatiga
  const currentStats = useMemo(
    () => calculateFatigueStats(basePitcherStats, pitchCount),
    [basePitcherStats, pitchCount]
  );

  const staminaColor = useMemo(() => getStaminaColor(fatigueLevel), [fatigueLevel]);

  // Calcular penalizaciones por atributo
  const getPenalty = (stat: keyof FatigueStats): number => {
    const base = basePitcherStats[stat] || 75;
    const current = currentStats[stat];
    return Math.round(((base - current) / base) * 100);
  };

  const velocityPenalty = getPenalty('velocidad');
  const controlPenalty = getPenalty('control');
  const movementPenalty = getPenalty('movimiento');

  return (
    <div className="w-full flex flex-col gap-2 sm:gap-3 p-2 sm:p-3 md:p-4 bg-[#0A0D0F]/60 border border-[#C5A059]/30 rounded-lg">
      {/* HEADER: Título y etiqueta de estado */}
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-mono text-[10px] sm:text-xs md:text-sm font-bold uppercase text-[#E6DFD3] tracking-wider">
          ⚙️ Stamina del Lanzador
        </h3>
        <span
          className="font-mono text-[8px] sm:text-[9px] md:text-[10px] font-bold px-2 py-1 rounded-xs uppercase tracking-wide"
          style={{ color: staminaColor.color, backgroundColor: staminaColor.bgColor }}
        >
          {staminaColor.label}
        </span>
      </div>

      {/* STAMINA BAR - Con animación y color dinámico */}
      <div className="flex flex-col gap-1">
        {/* Barra principal */}
        <div className="w-full h-4 sm:h-5 md:h-6 bg-[#0A0D0F]/80 border border-[#C5A059]/40 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full transition-all duration-500"
            style={{ backgroundColor: staminaColor.color }}
            initial={{ width: '0%' }}
            animate={{ width: `${fatigueLevel}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          >
            {/* Efecto de brillo interno */}
            <div className="w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          </motion.div>
        </div>

        {/* Porcentaje de fatiga */}
        <div className="flex justify-between items-center px-1">
          <span className="font-mono text-[8px] sm:text-[9px] md:text-[10px] text-[#E6DFD3]/70">
            Fatiga
          </span>
          <span
            className="font-mono text-[8px] sm:text-[9px] md:text-[10px] font-bold"
            style={{ color: staminaColor.color }}
          >
            {fatigueLevel.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* PITCH COUNT - Contador de lanzamientos */}
      <div className="flex items-center justify-between gap-2 px-2 py-1.5 bg-[#121619]/60 border border-[#C5A059]/20 rounded-xs">
        <span className="font-mono text-[8px] sm:text-[9px] md:text-[10px] text-[#E6DFD3]/70 uppercase tracking-wide">
          📊 Lanzamientos
        </span>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-xs sm:text-sm md:text-base font-bold text-[#C5A059]">
            {pitchCount}
          </span>
          <span className="font-mono text-[8px] sm:text-[9px] md:text-[10px] text-[#E6DFD3]/50">
            / 60 umbral
          </span>
        </div>
      </div>

      {/* FATIGUE STATS - Estadísticas con penalizaciones */}
      <div className="grid grid-cols-3 gap-1 sm:gap-1.5">
        {/* Velocidad */}
        <motion.div
          className="flex flex-col items-center gap-1 p-1.5 sm:p-2 md:p-2.5 bg-[#121619]/60 border rounded-xs"
          style={{
            borderColor: velocityPenalty > 0 ? '#EF4444' : '#C5A059',
            backgroundColor: velocityPenalty > 0 ? '#1F0F0F' : '#0A0D0F',
          }}
          animate={{
            boxShadow:
              velocityPenalty > 0
                ? '0 0 8px rgba(239, 68, 68, 0.3)'
                : '0 0 8px rgba(197, 160, 89, 0.1)',
          }}
        >
          <span className="font-mono text-[7px] sm:text-[8px] md:text-[9px] font-bold uppercase text-[#E6DFD3]/70">
            VELO
          </span>
          <span className="font-mono text-xs sm:text-sm md:text-base font-bold text-[#C5A059]">
            {currentStats.velocidad}
          </span>
          {velocityPenalty > 0 && (
            <span className="font-mono text-[7px] sm:text-[8px] md:text-[9px] text-[#EF4444] font-bold">
              -{velocityPenalty}%
            </span>
          )}
        </motion.div>

        {/* Control */}
        <motion.div
          className="flex flex-col items-center gap-1 p-1.5 sm:p-2 md:p-2.5 bg-[#121619]/60 border rounded-xs"
          style={{
            borderColor: controlPenalty > 0 ? '#EF4444' : '#C5A059',
            backgroundColor: controlPenalty > 0 ? '#1F0F0F' : '#0A0D0F',
          }}
          animate={{
            boxShadow:
              controlPenalty > 0
                ? '0 0 8px rgba(239, 68, 68, 0.3)'
                : '0 0 8px rgba(197, 160, 89, 0.1)',
          }}
        >
          <span className="font-mono text-[7px] sm:text-[8px] md:text-[9px] font-bold uppercase text-[#E6DFD3]/70">
            CTRL
          </span>
          <span className="font-mono text-xs sm:text-sm md:text-base font-bold text-[#C5A059]">
            {currentStats.control}
          </span>
          {controlPenalty > 0 && (
            <span className="font-mono text-[7px] sm:text-[8px] md:text-[9px] text-[#EF4444] font-bold">
              -{controlPenalty}%
            </span>
          )}
        </motion.div>

        {/* Movimiento */}
        <motion.div
          className="flex flex-col items-center gap-1 p-1.5 sm:p-2 md:p-2.5 bg-[#121619]/60 border rounded-xs"
          style={{
            borderColor: movementPenalty > 0 ? '#EF4444' : '#C5A059',
            backgroundColor: movementPenalty > 0 ? '#1F0F0F' : '#0A0D0F',
          }}
          animate={{
            boxShadow:
              movementPenalty > 0
                ? '0 0 8px rgba(239, 68, 68, 0.3)'
                : '0 0 8px rgba(197, 160, 89, 0.1)',
          }}
        >
          <span className="font-mono text-[7px] sm:text-[8px] md:text-[9px] font-bold uppercase text-[#E6DFD3]/70">
            MVTO
          </span>
          <span className="font-mono text-xs sm:text-sm md:text-base font-bold text-[#C5A059]">
            {currentStats.movimiento}
          </span>
          {movementPenalty > 0 && (
            <span className="font-mono text-[7px] sm:text-[8px] md:text-[9px] text-[#EF4444] font-bold">
              -{movementPenalty}%
            </span>
          )}
        </motion.div>
      </div>

      {/* FATIGUE WARNING - Mensaje de alerta si está crítico */}
      {fatigueLevel > 85 && (
        <motion.div
          className="px-2 py-1.5 bg-[#7F1D1D]/40 border border-[#EF4444]/50 rounded-xs text-center"
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <p className="font-mono text-[8px] sm:text-[9px] md:text-[10px] text-[#EF4444] font-bold uppercase">
            ⚠️ Considera cambiar de lanzador
          </p>
        </motion.div>
      )}
    </div>
  );
};

PitcherStaminaBar.displayName = 'PitcherStaminaBar';
