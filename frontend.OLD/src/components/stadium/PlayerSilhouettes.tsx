import React from 'react';

interface SilhouetteProps {
  type: 'pitcher_rhp' | 'pitcher_lhp' | 'batter_rhh' | 'batter_lhh';
  className?: string;
}

export const PlayerSilhouette: React.FC<SilhouetteProps> = ({ type, className = "w-full h-full" }) => {
  switch (type) {
    case 'pitcher_rhp': // Lanzador Diestro (Windup clásico)
      return (
        <svg viewBox="0 0 200 250" fill="currentColor" className={className}>
          <path d="M110 40 c-15 0 -25 10 -25 25 c0 15 10 25 25 25 c15 0 25 -10 25 -25 c0 -15 -10 -25 -25 -25z M95 90 l-25 40 l30 10 l-10 60 l20 -10 l15 -50 l15 50 l20 10 l-10 -60 l30 -10 l-25 -40z" />
        </svg>
      );

    case 'pitcher_lhp': // Lanzador Zurdo (Perfil invertido)
      return (
        <svg viewBox="0 0 200 250" fill="currentColor" className={className}>
          <path d="M90 40 c15 0 25 10 25 25 c0 15 -10 25 -25 25 c-15 0 -25 -10 -25 -25 c0 -15 10 -25 25 -25z M105 90 l25 40 l-30 10 l10 60 l-20 -10 l-15 -50 l-15 50 l-20 -10 l10 -60 l-30 -10 l25 -40z" />
        </svg>
      );

    case 'batter_rhh': // Bateador Derecho (Stance clásico mirando a la izq)
      return (
        <svg viewBox="0 0 200 250" fill="currentColor" className={className}>
          <path d="M120 45 c-12 0 -20 8 -20 20 c0 12 8 20 20 20 c12 0 20 -8 20 -20 c0 -12 -8 -20 -20 -20z M110 85 l-20 35 l25 15 l-35 75 l20 10 l20 -55 l20 55 l20 -10 l-35 -75 l25 -15 l-20 -35z" />
        </svg>
      );

    case 'batter_lhh': // Bateador Zurdo (Stance invertido mirando a la der)
      return (
        <svg viewBox="0 0 200 250" fill="currentColor" className={className}>
          <path d="M80 45 c12 0 20 8 20 20 c0 12 -8 20 -20 20 c-12 0 -20 -8 -20 -20 c0 -12 8 -20 20 -20z M90 85 l20 35 l-25 15 l35 75 l-20 10 l-20 -55 l-20 55 l-20 -10 l35 -75 l-25 -15 l20 -35z" />
        </svg>
      );

    default:
      return null;
  }
};