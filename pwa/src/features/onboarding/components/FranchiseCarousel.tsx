import { useRef } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { Franchise } from '@/shared/api/types'

// Tarjetas cuadradas: ancho fijo compacto + aspect-square (alto = ancho).
const CARD_SIZE_CLASS = 'aspect-square w-36 sm:w-40 md:w-44'
const COMPACT_CARD_SIZE_CLASS =
  'h-28 w-28 sm:h-32 sm:w-32 md:h-30 md:w-30 desktop:h-32 desktop:w-32'

interface Props {
  teams: Franchise[]
  selectedTeamId: string
  onSelectTeam: (teamId: string) => void
  compact?: boolean
}

export function FranchiseCarousel({ teams, selectedTeamId, onSelectTeam, compact = false }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const scrollByCard = (direction: 1 | -1) => {
    const el = scrollRef.current
    if (!el) return
    const cardWidth = el.querySelector<HTMLElement>('button')?.offsetWidth ?? 160
    el.scrollBy({ left: direction * (cardWidth + 12), behavior: 'smooth' })
  }

  return (
    <div
      className={`relative rounded-2xl border border-koshien-border ${compact ? 'bg-koshien-dark/45 p-2.5 backdrop-blur-md sm:p-3' : 'bg-koshien-dark/60 p-3 sm:p-4'}`}
    >
      <div
        ref={scrollRef}
        role="listbox"
        aria-label="Franquicias de la liga"
        tabIndex={0}
        className={`flex snap-x snap-mandatory overflow-x-auto scroll-smooth scroll-px-2 no-scrollbar ${compact ? 'gap-2.5 px-1 py-1 sm:gap-3 sm:px-5 sm:py-2 sm:scroll-px-5' : 'gap-3 sm:scroll-px-4'}`}
      >
        {teams.map((team) => {
          const selected = team.id === selectedTeamId
          return (
            <button
              key={team.id}
              type="button"
              role="option"
              aria-selected={selected}
              onClick={() => onSelectTeam(team.id)}
              className={`${compact ? COMPACT_CARD_SIZE_CLASS : CARD_SIZE_CLASS} relative flex shrink-0 snap-start flex-col justify-center rounded-xl border-2 text-left transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${compact ? 'p-2.5 sm:p-3' : 'p-3'} ${
                selected
                  ? compact
                    ? 'scale-[1.01] border-koshien-gold bg-koshien-green/80 ring-1 ring-koshien-gold/45 shadow-[0_0_18px_rgba(197,160,89,0.45)] backdrop-blur-sm'
                    : 'scale-[1.03] border-koshien-gold bg-koshien-green ring-2 ring-koshien-gold/45 shadow-[0_0_22px_rgba(197,160,89,0.5)]'
                  : compact
                    ? 'border-koshien-border bg-koshien-dark/55 opacity-70 backdrop-blur-sm hover:border-koshien-gold/50 hover:opacity-100'
                    : 'border-koshien-border bg-koshien-dark/80 opacity-70 hover:border-koshien-gold/50 hover:opacity-100'
              }`}
            >
              {selected ? (
                <span className="absolute right-2 top-2 rounded-full bg-koshien-gold px-1.5 py-0.5 font-sports text-[10px] font-bold text-koshien-dark shadow">
                  ✓
                </span>
              ) : null}
              <span className="flex w-full items-center justify-between">
                <span
                  aria-hidden
                  className={`${compact ? 'h-3.5 w-3.5' : 'h-4 w-4'} inline-block rounded-full border border-white/30`}
                  style={{ backgroundColor: team.color }}
                />
                <span
                  className={`font-vintage uppercase tracking-widest text-koshien-gold ${compact ? 'text-[8px] sm:text-[9px]' : 'text-[10px]'}`}
                >
                  {team.badge}
                </span>
              </span>
              <span
                className={`font-sports font-bold uppercase leading-tight text-koshien-chalk ${compact ? 'mt-1.5 text-xs sm:text-sm' : 'mt-2 text-sm'}`}
              >
                {team.name}
              </span>
              <span
                className={`font-vintage uppercase tracking-widest text-koshien-cream/60 ${compact ? 'text-[8px] sm:text-[9px]' : 'text-[10px]'}`}
              >
                {team.city}
              </span>
              <span
                className={`mt-1 font-sports font-bold text-koshien-gold ${compact ? 'text-sm sm:text-base' : 'text-base'}`}
              >
                OVR {team.ovr}
              </span>
            </button>
          )
        })}
      </div>

      <button
        type="button"
        aria-label="Anterior"
        onClick={() => scrollByCard(-1)}
        className="absolute left-1 top-1/2 hidden -translate-y-1/2 items-center justify-center rounded-full border border-koshien-border bg-koshien-dark/90 p-1.5 text-koshien-cream shadow-scoreboard transition-colors hover:text-koshien-gold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:flex"
      >
        <ChevronLeft className="h-5 w-5" aria-hidden />
      </button>

      <button
        type="button"
        aria-label="Siguiente"
        onClick={() => scrollByCard(1)}
        className="absolute right-1 top-1/2 hidden -translate-y-1/2 items-center justify-center rounded-full border border-koshien-border bg-koshien-dark/90 p-1.5 text-koshien-cream shadow-scoreboard transition-colors hover:text-koshien-gold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold sm:flex"
      >
        <ChevronRight className="h-5 w-5" aria-hidden />
      </button>
    </div>
  )
}
