import React from 'react';
import { TacticalCard, PlayerRole } from '../../types/stadium';

interface TacticalHandProps {
  tacticalHand: TacticalCard[];
  selectedTacticalId: string | null;
  role: PlayerRole;
  isIBB: boolean;
  onSelectTactical: (id: string) => void;
  onSubmitPlay: () => void;
}

export const TacticalHand: React.FC<TacticalHandProps> = ({
  tacticalHand,
  selectedTacticalId,
  role,
  isIBB,
  onSelectTactical,
  onSubmitPlay,
}) => {
  return (
    <footer className="w-full max-w-6xl mx-auto bg-[#0A0D0F] border border-[#C5A059]/60 p-3.5 flex flex-col md:flex-row justify-between items-center gap-4 mt-3 shadow-2xl">
      <div className="flex flex-col">
        <span className="font-mono text-xs text-[#C5A059] uppercase font-bold">
          CARTAS TÁCTICAS EN MANO
        </span>
        <span className="font-mono text-[10px] text-[#E6DFD3]/70">
          SELECCIONA PARA ACTIVAR TÁCTICA EN LA JUGADA
        </span>
      </div>

      {/* Baraja de Cartas */}
      <div className="flex gap-3 overflow-x-auto py-1">
        {tacticalHand.map((card) => {
          const isSelected = selectedTacticalId === card.id;
          return (
            <div
              key={card.id}
              onClick={() => onSelectTactical(card.id)}
              className={`bg-[#0A0D0F] border-2 ${card.color} ${
                isSelected ? 'ring-2 ring-[#C5A059] -translate-y-2' : ''
              } hover:-translate-y-1 p-3 w-40 text-center cursor-pointer transition-all shadow-xl flex flex-col justify-between h-36`}
            >
              <div>
                <div className="flex justify-between items-center font-mono text-[9px] border-b border-[#2C3E35] pb-1 mb-2">
                  <span className="font-bold">{card.type}</span>
                  <span>⚡{card.cost}</span>
                </div>
                <div className="text-3xl my-1">{card.icon}</div>
                <h5 className="font-sports text-base text-[#F7F5F0] leading-tight uppercase font-bold">
                  {card.name}
                </h5>
              </div>
              <p className="font-mono text-[9px] text-[#E6DFD3] leading-tight mt-1">
                {card.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Botón de Acción Principal */}
      <div className="flex flex-col items-center">
        <button
          type="button"
          onClick={onSubmitPlay}
          className="bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] px-8 py-3.5 font-sports text-3xl text-[#F7F5F0] tracking-widest shadow-xl transition-all active:scale-95 flex items-center gap-3"
        >
          {isIBB
            ? 'INTENCIONAL ⚾'
            : role === 'PITCHER'
            ? 'LANZAR ⚾'
            : 'BATEAR 💥'}
        </button>
        <span className="font-mono text-[9px] text-[#C5A059] uppercase tracking-wider mt-1">
          CONFIRMA LA JUGADA
        </span>
      </div>
    </footer>
  );
};