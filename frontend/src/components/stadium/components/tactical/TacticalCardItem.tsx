/**
 * TacticalCardItem - Individual tactical card display
 * 
 * Sub-component of TacticalHand (extracted for clarity)
 * Shows single tactical card with type, icon, name, and description
 * 
 * @component
 * @example
 * <TacticalCardItem
 *   card={tacticalCard}
 *   isSelected={false}
 *   disabled={false}
 *   onSelect={() => setSelected(card.id)}
 * />
 */

import React from 'react';
import type { TacticalCard } from '../../types/stadium.types';

interface TacticalCardItemProps {
  card: TacticalCard;
  isSelected: boolean;
  disabled: boolean;
  onSelect: (id: string) => void;
}

export const TacticalCardItem: React.FC<TacticalCardItemProps> = ({
  card,
  isSelected,
  disabled,
  onSelect,
}) => {
  return (
    <div
      onClick={() => !disabled && onSelect(card.id)}
      className={`bg-[#0A0D0F] border-2 ${card.color} ${
        isSelected ? 'ring-2 ring-[#C5A059] -translate-y-2' : ''
      } hover:-translate-y-1 p-3 w-40 text-center transition-all shadow-xl flex flex-col justify-between h-36 ${
        disabled ? 'opacity-40 cursor-not-allowed pointer-events-none' : 'cursor-pointer'
      }`}
    >
      {/* Header: Type + Cost */}
      <div>
        <div className="flex justify-between items-center font-mono text-[9px] border-b border-[#2C3E35] pb-1 mb-2">
          <span className="font-bold">{card.type}</span>
          <span>⚡{card.cost}</span>
        </div>

        {/* Icon */}
        <div className="text-3xl my-1">{card.icon}</div>

        {/* Name */}
        <h5 className="font-sports text-base text-[#F7F5F0] leading-tight uppercase font-bold">
          {card.name}
        </h5>
      </div>

      {/* Description */}
      <p className="font-mono text-[9px] text-[#E6DFD3] leading-tight mt-1">
        {card.desc}
      </p>
    </div>
  );
};

TacticalCardItem.displayName = 'TacticalCardItem';
