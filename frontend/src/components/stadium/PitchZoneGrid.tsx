import React from 'react';
import { PitchType, PlayerRole } from '../../types/stadium';

interface PitchZoneGridProps {
  role: PlayerRole;
  selectedZone: number;
  selectedPitch: PitchType;
  onSelectZone: (zone: number) => void;
  onSelectPitch: (pitch: PitchType) => void;
  repertoire?: { pitch_type: string; velocity?: number }[];
}

export const PitchZoneGrid: React.FC<PitchZoneGridProps> = ({
  role,
  selectedZone,
  selectedPitch,
  onSelectZone,
  onSelectPitch,
  repertoire,
}) => {
  // Si la carta tiene repertorio real definido desde la DB, usamos esos lanzamientos.
  // De lo contrario, usamos una lista segura de fallbacks universales.
  const availablePitches: string[] =
    repertoire && repertoire.length > 0
      ? repertoire.map((p) => p.pitch_type)
      : ['4-SEAM', 'SLIDER', 'CHANGE'];

  return (
    <div className="z-10 flex flex-col items-center gap-3 my-auto">
      {role === 'PITCHER' && (
        <div className="flex flex-wrap justify-center gap-1 bg-[#0A0D0F] p-1 border border-[#2C3E35]">
          {availablePitches.map((pitch: string) => (
            <button
              key={pitch}
              type="button"
              onClick={() => onSelectPitch(pitch)}
              className={`px-3 py-1 font-mono text-[10px] uppercase transition-colors cursor-pointer ${
                selectedPitch === pitch
                  ? 'bg-[#1A3323] text-[#C5A059] border border-[#C5A059] font-bold shadow-[0_0_8px_rgba(197,160,89,0.5)]'
                  : 'text-[#E6DFD3] opacity-60 hover:opacity-100'
              }`}
            >
              {pitch}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onSelectPitch('IBB')}
            className={`px-2 py-1 font-mono text-[10px] uppercase transition-colors cursor-pointer ${
              selectedPitch === 'IBB'
                ? 'bg-[#C5A059] text-[#121619] font-bold border border-[#F7F5F0]'
                : 'text-[#C5A059] border border-[#C5A059]/40 opacity-80'
            }`}
          >
            IBB (INTENC.)
          </button>
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
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((zone: number) => (
            <button
              key={zone}
              type="button"
              onClick={() => onSelectZone(zone)}
              className={`w-16 h-16 border flex items-center justify-center font-mono text-xs transition-all cursor-pointer ${
                selectedZone === zone
                  ? 'border-[#C5A059] bg-[#1A3323] text-[#C5A059] font-bold shadow-[0_0_15px_rgba(197,160,89,0.6)]'
                  : 'border-[#2C3E35] text-[#E6DFD3] hover:border-[#C5A059]/60'
              }`}
            >
              Z{zone}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};