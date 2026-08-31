import { useRef } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { Franchise } from '@/shared/api/types'

// Tarjetas cuadradas: ancho fijo compacto + aspect-square (alto = ancho).
const CARD_SIZE_CLASS = 'aspect-square w-36 sm:w-40 md:w-44'

interface Props {
  teams: Franchise[]
  selectedTeamId: string
  onSelectTeam: (teamId: string) => void
}

export function FranchiseCarousel({ teams, selectedTeamId, onSelectTeam }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const scrollByCard = (direction: 1 | -1) => {
    const el = scrollRef.current
    if (!el) return
    const cardWidth = el.querySelector<HTMLElement>('button')?.offsetWidth ?? 160
    el.scrollBy({ left: direction * (cardWidth + 12), behavior: 'smooth' })
  }

  return (
    <div className="relative rounded-2xl border border-koshien-border bg-koshien-dark/60 p-3 sm:p-4">
      <div
        ref={scrollRef}
        role="listbox"
        aria-label="Franquicias de la liga"
        tabIndex={0}
        className="flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-smooth scroll-px-2 no-scrollbar sm:scroll-px-4"
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
              className={`${CARD_SIZE_CLASS} flex shrink-0 snap-start flex-col justify-center rounded-xl border-2 p-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
                selected
                  ? 'border-koshien-gold bg-koshien-green'
                  : 'border-koshien-border bg-koshien-dark/80 hover:border-koshien-gold/50'
              }`}
            >
              <span className="flex w-full items-center justify-between">
                <span
                  aria-hidden
                  className="inline-block h-4 w-4 rounded-full border border-white/30"
                  style={{ backgroundColor: team.color }}
                />
                <span className="font-vintage text-[10px] uppercase tracking-widest text-koshien-gold">
                  {team.badge}
                </span>
              </span>
              <span className="mt-2 font-sports text-sm font-bold uppercase leading-tight text-koshien-chalk">
                {team.name}
              </span>
              <span className="font-vintage text-[10px] uppercase tracking-widest text-koshien-cream/60">
                {team.city}
              </span>
              <span className="mt-1 font-sports text-base font-bold text-koshien-gold">
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
