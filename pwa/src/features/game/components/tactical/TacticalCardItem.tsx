import type { TacticalCard } from '@/shared/api/types'

interface TacticalCardItemProps {
  card: TacticalCard
  isSelected: boolean
  disabled: boolean
  onSelect: (id: string) => void
}

export function TacticalCardItem({ card, isSelected, disabled, onSelect }: TacticalCardItemProps) {
  return (
    <button
      type="button"
      aria-pressed={isSelected}
      disabled={disabled}
      onClick={() => !disabled && onSelect(card.id)}
      className={`flex h-36 w-40 flex-col justify-between border-2 ${card.color} bg-koshien-dark p-3 text-center shadow-xl transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
        isSelected ? '-translate-y-2 ring-2 ring-koshien-gold' : ''
      } hover:-translate-y-1 ${
        disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'
      }`}
    >
      <div>
        <div className="mb-2 flex items-center justify-between border-b border-koshien-border pb-1 font-vintage text-[9px]">
          <span className="font-bold">{card.type}</span>
          <span>⚡{card.cost}</span>
        </div>

        <div className="my-1 text-3xl">{card.icon}</div>

        <h5 className="font-sports text-base font-bold uppercase leading-tight text-koshien-chalk">
          {card.name}
        </h5>
      </div>

      <p className="mt-1 font-vintage text-[9px] leading-tight text-koshien-cream">
        {card.desc}
      </p>
    </button>
  )
}
