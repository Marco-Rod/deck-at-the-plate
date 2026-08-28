/**
 * Stadium Components - Shared Constants
 * 
 * Constantes centralizadas para colores, tamaños, y configuración visual
 * para facilitar mantenimiento y consistencia en toda la UI del stadium.
 */

import type { RarityConfig, Dict } from '../types/stadium.types';

// ============================================================================
// COLOR PALETTE
// ============================================================================

export const COLORS = {
  // Backgrounds
  PRIMARY_DARK: '#0A0D0F',       // Background principal muy oscuro
  SECONDARY_DARK: '#121619',     // Secondary backgrounds
  SURFACE_DARK: '#0A0D0F',       // Superficie oscura con opacidad
  
  // Text
  TEXT_PRIMARY: '#F7F5F0',       // Texto principal muy claro
  TEXT_SECONDARY: '#E6DFD3',     // Texto secundario claro
  TEXT_MUTED: '#C5A059',         // Texto apagado (oro)
  
  // Accents & Interactive
  ACCENT_GOLD: '#C5A059',        // Oro - bordes activos, interactivos
  ACCENT_GREEN: '#1A3323',       // Verde oscuro - estados selected
  ACCENT_ERROR: '#EF4444',       // Rojo para errores
  
  // Borders
  BORDER_SUBTLE: '#2C3E35',      // Bordes sutiles, inactivos
  BORDER_STRONG: '#C5A059',      // Bordes activos - oro
  
  // Status
  STATUS_CONNECTED: '#10B981',   // Verde - conexión activa
  STATUS_DISCONNECTED: '#EF4444',// Rojo - desconectado
} as const;

export const RARITY_COLORS: Dict<RarityConfig> = {
  DIAMOND: {
    borderColor: '#9966FF',
    shadowColor: 'rgba(153, 102, 255, 0.8)',
    glowColor: '#9966FF',
  },
  GOLD: {
    borderColor: '#FFD700',
    shadowColor: 'rgba(255, 215, 0, 0.7)',
    glowColor: '#FFD700',
  },
  SILVER: {
    borderColor: '#C0C0C0',
    shadowColor: 'rgba(192, 192, 192, 0.6)',
    glowColor: '#C0C0C0',
  },
  BRONZE: {
    borderColor: '#CD7F32',
    shadowColor: 'rgba(205, 127, 50, 0.6)',
    glowColor: '#CD7F32',
  },
  COMMON: {
    borderColor: '#808080',
    shadowColor: 'rgba(128, 128, 128, 0.5)',
    glowColor: '#808080',
  },
} as const;

// ============================================================================
// TYPOGRAPHY
// ============================================================================

export const TYPOGRAPHY = {
  // Titles & Headers
  TITLE_H1: 'font-sports text-4xl text-[#F7F5F0] uppercase tracking-wider leading-none',
  TITLE_H2: 'font-sports text-2xl text-[#F7F5F0] uppercase tracking-wider',
  TITLE_H3: 'font-sports text-xl text-[#F7F5F0] uppercase',
  
  // Body Text
  BODY_REGULAR: 'font-mono text-base text-[#F7F5F0]',
  BODY_SECONDARY: 'font-mono text-sm text-[#E6DFD3]',
  
  // Labels & Small Text
  LABEL_SMALL: 'font-mono text-[10px] text-[#E6DFD3] uppercase tracking-wider',
  LABEL_TINY: 'font-mono text-[8px] text-[#E6DFD3] uppercase tracking-widest',
  
  // Data/Monospace
  DATA_MONO: 'font-mono text-xs text-[#F7F5F0]',
} as const;

// ============================================================================
// SPACING
// ============================================================================

export const SPACING = {
  // Padding
  PADDING_XS: 'p-1.5',    // 6px
  PADDING_SM: 'p-2',      // 8px
  PADDING_MD: 'p-3',      // 12px
  PADDING_LG: 'p-4',      // 16px
  PADDING_XL: 'p-6',      // 24px
  
  // Gap/Margin
  GAP_SM: 'gap-2',        // 8px
  GAP_MD: 'gap-3',        // 12px
  GAP_LG: 'gap-4',        // 16px
  GAP_XL: 'gap-6',        // 24px (Propuesta 1)
  
  // Vertical spacing
  VERTICAL_SM: 'my-1.5',  // 6px
  VERTICAL_MD: 'my-2',    // 8px
  VERTICAL_LG: 'my-4',    // 16px
} as const;

// ============================================================================
// COMPONENT SIZES
// ============================================================================

export const SIZES = {
  // Player Cards
  PLAYER_CARD_WIDTH: 'w-56',     // 224px
  PLAYER_CARD_HEIGHT: 'h-80',    // 320px
  
  // Grid Elements
  ZONE_SIZE: 'w-16 h-16',        // 64×64px (strike zones)
  GRID_CONTAINER_WIDTH: 'w-auto', // Flexible based on content
  
  // Buttons
  BUTTON_SM: 'px-3 py-1.5',      // Small buttons
  BUTTON_MD: 'px-4 py-2',        // Medium buttons
  BUTTON_LG: 'px-6 py-3',        // Large buttons
  
  // Borders
  BORDER_THIN: 'border',         // 1px
  BORDER_MEDIUM: 'border-2',     // 2px
  BORDER_THICK: 'border-4',      // 4px
} as const;

// ============================================================================
// ANIMATION CONFIG
// ============================================================================

export const ANIMATIONS = {
  // Durations (ms)
  DURATION_FAST: 200,
  DURATION_NORMAL: 1000,
  DURATION_SLOW: 2500,
  DURATION_VERY_SLOW: 10000,
  
  // Easing
  EASE_IN_OUT: 'easeInOut',
  EASE_LINEAR: 'linear',
  
  // Pulse/Glow
  PULSE_DURATION: 1.8,
  PULSE_REPEAT: 'Infinity',
  GLOW_MIN: '0 0 8px',
  GLOW_MAX: '0 0 16px',
  
  // Rotation
  ROTATION_DURATION: 10,
  ROTATION_FULL: 360,
} as const;

// ============================================================================
// GAME CONSTANTS
// ============================================================================

export const GAME_CONFIG = {
  // Inning
  DEFAULT_TOTAL_INNINGS: 9,
  
  // Strike Zone
  STRIKE_ZONES: [1, 2, 3, 4, 5, 6, 7, 8, 9],
  DEFAULT_ZONE: 5,
  ZONE_SIZE_PIXELS: 64,
  ZONE_GAP: 8,
  
  // Player Info
  STATS_TO_DISPLAY: 2,  // Only show 2 stats per card (Propuesta 1)
  
  // Animation Delays
  RESULT_DELAY_MS: 1000,
  OVERLAY_DURATION_DEFAULT: 2500,
  
  // Overlay Durations by Event
  OVERLAY_DURATIONS: {
    HOME_RUN: 1000 + 3500,      // 4500ms
    HIT_3B: 1000 + 3000,        // 4000ms
    HIT_2B: 1000 + 2800,        // 3800ms
    HIT_1B: 1000 + 2500,        // 3500ms
    STRIKEOUT: 1000 + 2800,     // 3800ms
    OUT_FLY: 1000 + 2500,       // 3500ms
    OUT_GROUND: 1000 + 2500,    // 3500ms
    WALK: 1000 + 2500,          // 3500ms
  },
} as const;

// ============================================================================
// SHADOW & EFFECTS
// ============================================================================

export const EFFECTS = {
  SHADOW_SM: 'shadow',
  SHADOW_MD: 'shadow-md',
  SHADOW_LG: 'shadow-lg',
  SHADOW_2XL: 'shadow-2xl',
  
  // Glow effect (custom inline styles)
  GLOW_SUBTLE: 'rgba(197, 160, 89, 0.4)',
  GLOW_MEDIUM: 'rgba(197, 160, 89, 0.7)',
  GLOW_STRONG: 'rgba(197, 160, 89, 0.8)',
} as const;

// ============================================================================
// BORDER RADIUS
// ============================================================================

export const BORDER_RADIUS = {
  NONE: 'rounded-none',
  SM: 'rounded-xs',
  MD: 'rounded-sm',
  LG: 'rounded-md',
} as const;

// ============================================================================
// Z-INDEX LAYERS
// ============================================================================

export const Z_INDEX = {
  BACKGROUND: 0,
  BASE_COMPONENTS: 10,
  MODALS: 30,
  DROPDOWNS: 20,
  OVERLAYS: 40,
  TOOLTIPS: 50,
} as const;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get rarity config by overall rating
 * @param overall - Player overall rating (0-99)
 * @returns RarityConfig with colors and shadow
 */
export function getRarityConfig(overall: number = 75): RarityConfig {
  if (overall >= 90) return RARITY_COLORS.DIAMOND;
  if (overall >= 85) return RARITY_COLORS.GOLD;
  if (overall >= 80) return RARITY_COLORS.SILVER;
  if (overall >= 75) return RARITY_COLORS.BRONZE;
  return RARITY_COLORS.COMMON;
}

/**
 * Get rarity label by overall rating
 * @param overall - Player overall rating
 * @returns String label (DIAMOND, GOLD, SILVER, BRONZE, COMMON)
 */
export function getRarityLabel(overall: number = 75): string {
  if (overall >= 90) return 'DIAMOND';
  if (overall >= 85) return 'GOLD';
  if (overall >= 80) return 'SILVER';
  if (overall >= 75) return 'BRONZE';
  return 'COMMON';
}

/**
 * Get overlay duration by event type
 * @param event - Event key from GAME_CONFIG.OVERLAY_DURATIONS
 * @returns Duration in milliseconds
 */
export function getOverlayDuration(event: string): number {
  const key = event.toUpperCase();
  return GAME_CONFIG.OVERLAY_DURATIONS[key as keyof typeof GAME_CONFIG.OVERLAY_DURATIONS] 
    || GAME_CONFIG.OVERLAY_DURATION_DEFAULT;
}
