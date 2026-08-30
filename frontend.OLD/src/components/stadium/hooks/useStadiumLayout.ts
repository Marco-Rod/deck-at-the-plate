/**
 * useStadiumLayout - Shared logic for stadium layout and styling
 * 
 * Hook que proporciona funciones compartidas para el cálculo de
 * estilos, dimensiones y disposición de componentes en el stadium.
 */

import { useMemo } from 'react';
import { getRarityConfig, getRarityLabel } from '../constants/stadium.constants';
import type { PlayerData, RarityConfig } from '../types/stadium.types';

// ============================================================================
// INTERFACES
// ============================================================================

interface UseStadiumLayoutResult {
  getRarityConfig: (overall: number) => RarityConfig;
  getRarityLabel: (overall: number) => string;
  getContainerClasses: (variant: 'compact' | 'normal' | 'spacious') => string;
  getResponsiveGap: (baseGap: string) => string;
  getPlayerCardClasses: (isSelected: boolean) => string;
}

// ============================================================================
// HOOK
// ============================================================================

/**
 * useStadiumLayout - Proporciona utilidades para layout y estilos
 * 
 * @returns {UseStadiumLayoutResult} Objeto con funciones de utilidad
 * 
 * @example
 * const { getRarityConfig, getContainerClasses } = useStadiumLayout();
 * const rarityConfig = getRarityConfig(player.overall);
 */
export function useStadiumLayout(): UseStadiumLayoutResult {
  
  /**
   * Get container classes based on variant (Propuesta 1)
   * - compact: gap-4 (16px) - espaciado comprimido
   * - normal: gap-6 (24px) - espaciado normal (Propuesta 1 default)
   * - spacious: gap-8 (32px) - espaciado generoso
   */
  const getContainerClasses = (variant: 'compact' | 'normal' | 'spacious' = 'normal'): string => {
    const baseClasses = 'flex justify-center items-start';
    const gapClasses = {
      compact: 'gap-4',
      normal: 'gap-6',  // Propuesta 1
      spacious: 'gap-8',
    };
    return `${baseClasses} ${gapClasses[variant]}`;
  };

  /**
   * Get responsive gap for different screen sizes
   * - Desktop: Full gap
   * - Tablet: Reduced gap
   * - Mobile: Minimal gap
   */
  const getResponsiveGap = (baseGap: string): string => {
    const gapMap = {
      'gap-4': 'gap-3 md:gap-4 lg:gap-4',
      'gap-6': 'gap-4 md:gap-5 lg:gap-6',  // Propuesta 1
      'gap-8': 'gap-5 md:gap-6 lg:gap-8',
    };
    return gapMap[baseGap as keyof typeof gapMap] || baseGap;
  };

  /**
   * Get player card classes with selection state
   */
  const getPlayerCardClasses = (isSelected: boolean): string => {
    const baseClasses = 'w-56 h-80 flex items-start transition-all duration-200';
    return isSelected 
      ? `${baseClasses} ring-2 ring-[#C5A059]` 
      : baseClasses;
  };

  // Memoize result for performance
  return useMemo(() => ({
    getRarityConfig,
    getRarityLabel,
    getContainerClasses,
    getResponsiveGap,
    getPlayerCardClasses,
  }), []);
}

// ============================================================================
// UTILITY HOOKS FOR SPECIFIC COMPONENTS
// ============================================================================

/**
 * useGameStateFormatting - Format game state values for display
 */
export function useGameStateFormatting() {
  return useMemo(() => ({
    formatBalls: (balls: number): string => String(balls).padStart(1, '0'),
    formatStrikes: (strikes: number): string => String(strikes).padStart(1, '0'),
    formatOuts: (outs: number): string => String(outs).padStart(1, '0'),
    formatInning: (current: number, total: number): string => `${current} / ${total}`,
    formatScore: (score: number): string => String(score).padStart(1, '0'),
  }), []);
}

/**
 * usePlayerCardOptimization - Optimize player card rendering
 */
export function usePlayerCardOptimization(player: PlayerData | null) {
  return useMemo(() => {
    if (!player) return null;
    
    return {
      displayName: player.name.toUpperCase(),
      displayNumber: `#${player.number}`,
      displayTeam: player.team || 'UNKNOWN',
      displayStats: player.stats?.slice(0, 2) || [],
      rarityCfg: getRarityConfig(player.overall),
      rarityLabel: getRarityLabel(player.overall),
    };
  }, [player]);
}

/**
 * useAnimationConfig - Get animation configuration for components
 */
export function useAnimationConfig(isActive: boolean, enableAnimations: boolean = true) {
  return useMemo(() => {
    if (!enableAnimations) {
      return {
        animate: {},
        transition: {},
        whileHover: {},
        whileTap: {},
      };
    }

    return {
      animate: isActive ? {
        scale: 1,
        opacity: 1,
      } : {},
      transition: {
        duration: 0.2,
        ease: 'easeInOut',
      },
      whileHover: {
        scale: 1.05,
      },
      whileTap: {
        scale: 0.95,
      },
    };
  }, [isActive, enableAnimations]);
}

// ============================================================================
// COMPONENT-SPECIFIC UTILITIES
// ============================================================================

/**
 * Utility para calcular clases Tailwind dinámicamente
 */
export function classNames(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

/**
 * Utility para aplicar estilos condicionales
 */
export function conditionalStyle(
  condition: boolean,
  trueStyle: string,
  falseStyle?: string
): string {
  return condition ? trueStyle : (falseStyle || '');
}
