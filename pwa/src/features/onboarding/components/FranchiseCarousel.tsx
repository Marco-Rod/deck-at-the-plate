import type { Franchise } from '@/shared/api/types'

interface Props {
  teams: Franchise[]
  selectedTeamId: string
  onSelectTeam: (teamId: string) => void
}

export function FranchiseCarousel({ teams, selectedTeamId, onSelectTeam }: Props) {
  return (
    <div
      role="listbox"
      aria-label="Franquicias de la liga"
      className="grid max-h-[45vh] grid-cols-2 gap-3 overflow-y-auto pr-1 sm:grid-cols-3 md:grid-cols-4"
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
            className={`flex flex-col items-start gap-1 rounded-xl border-2 p-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
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
            <span className="font-sports text-sm font-bold uppercase leading-tight text-koshien-chalk">
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
  )
}
