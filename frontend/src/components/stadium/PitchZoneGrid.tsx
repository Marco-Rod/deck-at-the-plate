import React from 'react';
import { motion } from 'framer-motion';
import { PitchType, PlayerRole } from '../../types/stadium';

interface PitchZoneGridProps {
  role: PlayerRole;
  selectedZone: number;
  selectedPitch: PitchType;
  onSelectZone: (zone: number) => void;
  onSelectPitch: (pitch: PitchType) => void;
  repertoire?: { pitch_type: string; velocity?: number }[];
  disabled?: boolean;
}

export const PitchZoneGrid: React.FC<PitchZoneGridProps> = ({
  role,
  selectedZone,
  selectedPitch,
  onSelectZone,
  onSelectPitch,
  repertoire,
  disabled = false,
}) => {
  // Si la carta tiene repertorio real definido desde la DB, usamos esos lanzamientos.
  // De lo contrario, usamos una lista segura de fallbacks universales.
  const availablePitches: string[] =
    repertoire && repertoire.length > 0
      ? repertoire.map((p) => p.pitch_type)
      : ['4-SEAM', 'SLIDER', 'CHANGE'];

  return (
    <div className={`z-10 flex flex-col items-center gap-3 my-auto transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
      {role === 'PITCHER' && (
        <div className="flex flex-wrap justify-center gap-1.5 bg-[#0A0D0F] p-1.5 border border-[#C5A059]/40 rounded-xs shadow-xl">
          {availablePitches.map((pitch: string) => {
            const isPitchSelected = selectedPitch === pitch;

            return (
              <motion.button
                key={pitch}
                type="button"
                onClick={() => onSelectPitch(pitch as PitchType)}
                className={`relative px-3 py-1.5 font-mono text-[10px] uppercase cursor-pointer rounded-xs overflow-hidden ${
                  isPitchSelected
                    ? 'bg-[#1A3323] text-[#C5A059] border border-[#C5A059] font-bold z-10'
                    : 'bg-[#0A0D0F] text-[#E6DFD3] border border-[#2C3E35] opacity-70 hover:opacity-100'
                }`}
                // Animación al pasar el cursor y al hacer clic
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                // Pulso luminoso constante si el lanzamiento está seleccionado
                animate={
                  isPitchSelected
                    ? {
                        boxShadow: [
                          '0 0 8px rgba(197, 160, 89, 0.4)',
                          '0 0 16px rgba(197, 160, 89, 0.8)',
                          '0 0 8px rgba(197, 160, 89, 0.4)',
                        ],
                      }
                    : { boxShadow: '0 0 0px rgba(0,0,0,0)' }
                }
                transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
              >
                <span className="relative z-10">{pitch}</span>
              </motion.button>
            );
          })}

          <motion.button
            type="button"
            onClick={() => onSelectPitch('IBB' as PitchType)}
            className={`relative px-2.5 py-1.5 font-mono text-[10px] uppercase cursor-pointer rounded-xs overflow-hidden ${
              selectedPitch === 'IBB'
                ? 'bg-[#C5A059] text-[#121619] font-bold border border-[#F7F5F0] z-10'
                : 'bg-[#0A0D0F] text-[#C5A059] border border-[#C5A059]/40 opacity-80 hover:opacity-100'
            }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            animate={
              selectedPitch === 'IBB'
                ? {
                    boxShadow: [
                      '0 0 8px rgba(197, 160, 89, 0.5)',
                      '0 0 18px rgba(247, 245, 240, 0.9)',
                      '0 0 8px rgba(197, 160, 89, 0.5)',
                    ],
                  }
                : { boxShadow: '0 0 0px rgba(0,0,0,0)' }
            }
            transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          >
            <span className="relative z-10">IBB (INTENC.)</span>
          </motion.button>
        </div>
      )}

      <div
        className={`bg-[#0A0D0F]/95 p-4 border-2 border-[#C5A059] shadow-2xl text-center transition-all ${
          selectedPitch === 'IBB' ? 'opacity-40 pointer-events-none' : ''
        }`}
      >
        <span className="font-mono text-[10px] text-[#C5A059] uppercase block mb-2 font-bold">
          {role === 'PITCHER'
            ? `UBICACIÓN: ZONA Z${selectedZone}`
            : 'PREDICE LA ZONA DE SWING'}
        </span>
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((zone: number) => {
            const isSelected = selectedZone === zone;

            return (
              <motion.button
                key={zone}
                type="button"
                onClick={() => onSelectZone(zone)}
                className={`relative w-16 h-16 border flex items-center justify-center font-mono text-xs cursor-pointer overflow-hidden ${
                  isSelected
                    ? 'border-[#C5A059] bg-[#1A3323] text-[#C5A059] font-bold z-10'
                    : 'border-[#2C3E35] text-[#E6DFD3] hover:border-[#C5A059]/60 bg-[#0A0D0F]'
                }`}
                // Animación de escala y relieve al pasar el cursor
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {/* Efecto de brillo de pulso constante cuando la zona está seleccionada */}
                {isSelected && (
                  <motion.div
                    className="absolute inset-0 border-2 border-[#C5A059] pointer-events-none"
                    animate={{
                      boxShadow: [
                        'inset 0 0 5px rgba(197, 160, 89, 0.4), 0 0 5px rgba(197, 160, 89, 0.4)',
                        'inset 0 0 15px rgba(197, 160, 89, 0.9), 0 0 20px rgba(197, 160, 89, 0.8)',
                        'inset 0 0 5px rgba(197, 160, 89, 0.4), 0 0 5px rgba(197, 160, 89, 0.4)',
                      ],
                    }}
                    transition={{
                      duration: 1.8,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  />
                )}

                {/* Anillo de mira táctica flotante alrededor de la zona seleccionada */}
                {isSelected && (
                  <motion.div
                    className="absolute inset-1 border border-dashed border-[#C5A059]/70 pointer-events-none rounded-xs"
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 10,
                      repeat: Infinity,
                      ease: 'linear',
                    }}
                  />
                )}

                <span className="relative z-10">Z{zone}</span>
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
};