import React from 'react';
import { PitchType, PlayerRole, PITCH_TYPE_LABELS } from '../../types/stadium';

interface PitchZoneGridProps {
  role: PlayerRole;
  selectedZone: number;
  selectedPitch: PitchType;
  onSelectZone: (zone: number) => void;
  onSelectPitch: (pitch: PitchType) => void;
}

export const PitchZoneGrid: React.FC<PitchZoneGridProps> = ({
  role,
  selectedZone,
  selectedPitch,
  onSelectZone,
  onSelectPitch,
}) => {
  // Códigos MLB estándar — deben coincidir con PitchType en types/stadium.ts
  const pitches: PitchType[] = ['FF', 'SL', 'CU', 'CH'];

  return (
    <div className="z-10 flex flex-col items-center gap-3 my-auto">
      {role === 'PITCHER' && (
        <div className="flex gap-1 bg-[#0A0D0F] p-1 border border-[#2C3E35]">
          {pitches.map((pitch: PitchType) => (
            <button
              key={pitch}
              type="button"
              onClick={() => onSelectPitch(pitch)}
              className={`px-3 py-1 font-mono text-[10px] uppercase transition-colors ${
                selectedPitch === pitch
                  ? 'bg-[#1A3323] text-[#C5A059] border border-[#C5A059]'
                  : 'text-[#E6DFD3] opacity-60'
              }`}
            >
              {PITCH_TYPE_LABELS[pitch]}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onSelectPitch('IBB')}
            className={`px-2 py-1 font-mono text-[10px] uppercase transition-colors ${
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
              className={`w-16 h-16 border flex items-center justify-center font-mono text-xs transition-all ${
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