import { motion } from 'framer-motion'

interface TacticalCardsAreaProps {
  hand: string[]
  selectedTacticalId: string | null
  disabled: boolean
  onSelect: (id: string) => void
}

export function TacticalCardsArea({
  hand,
  selectedTacticalId,
  disabled,
  onSelect,
}: TacticalCardsAreaProps) {
  const slots: Array<string | null> = hand.length > 0 ? hand : new Array(3).fill(null)
  return (
    <div className="flex gap-2">
      {slots.map((id, index) => {
        const isSelected = id != null && selectedTacticalId === id
        return (
          <motion.button
            key={id != null ? `${id}-${index}` : `empty-${index}`}
            type="button"
            disabled={disabled || id == null}
            aria-pressed={id != null ? isSelected : undefined}
            onClick={() => id != null && onSelect(id)}
            whileHover={id == null ? undefined : { scale: 1.04, y: -2 }}
            whileTap={id == null ? undefined : { scale: 0.96 }}
            className={`relative flex h-32 w-24 flex-col items-center justify-between rounded border p-1.5 text-center shadow-xl transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:h-36 sm:w-28 lg:h-28 lg:w-20 ${id == null ? 'border-dashed border-koshien-border bg-koshien-dark/20 opacity-40' : isSelected ? 'border-2 border-koshien-gold bg-koshien-green/30 shadow-[0_0_14px_rgba(197,160,89,0.5)]' : 'border border-koshien-gold/50 bg-koshien-dark/70 hover:border-koshien-gold'}`}
          >
            {id != null && (
              <>
                <span className="text-xl sm:text-2xl lg:text-lg">🃏</span>
                <span className="font-sports text-xs font-bold uppercase text-koshien-gold sm:text-sm lg:text-[11px]">
                  {id}
                </span>
                <span className="font-vintage text-[8px] uppercase text-koshien-muted">
                  táctica
                </span>
              </>
            )}
          </motion.button>
        )
      })}
    </div>
  )
}

export function LanzarButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.65 }}
      className="flex flex-col items-center gap-2 lg:gap-1"
    >
      <button
        type="button"
        onClick={onClick}
        className="relative flex min-h-[64px] min-w-[150px] flex-col items-center justify-center rounded border-2 border-koshien-orange bg-koshien-dark/80 text-center font-sports text-2xl font-bold uppercase tracking-wider text-koshien-chalk shadow-[0_0_12px_rgba(242,161,58,0.3)] transition-all hover:bg-koshien-orange/10 hover:shadow-[0_0_16px_rgba(242,161,58,0.5)] active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:min-h-[78px] sm:min-w-[190px] sm:text-3xl lg:min-h-[56px] lg:min-w-[140px] lg:text-xl"
      >
        <span>{label}</span>
      </button>
    </motion.div>
  )
}
