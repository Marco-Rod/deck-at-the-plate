import type { BatterStats } from '@/shared/api/types'

export interface LineupPlayer {
  id?: string
  name: string
  number: string
  photo?: string
  overall?: number
  position?: string
}

interface LineupPanelProps {
  lineup: LineupPlayer[]
  stats: Record<string, BatterStats>
}

export function LineupPanel({ lineup, stats }: LineupPanelProps) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-sm border border-koshien-gold/30 bg-koshien-dark/95">
      <div className="flex-1 overflow-y-auto">
        {lineup && lineup.length > 0 ? (
          lineup.map((player, idx) => {
            const playerStats = player.id ? stats[player.id] : undefined
            const abh = playerStats ? `${playerStats.at_bats}-${playerStats.hits}` : '0-0'

            const activeStats = playerStats
              ? [
                  playerStats.hits > 0 && `H:${playerStats.hits}`,
                  playerStats.home_runs > 0 && `HR:${playerStats.home_runs}`,
                  playerStats.walks > 0 && `BB:${playerStats.walks}`,
                  playerStats.rbi > 0 && `RBI:${playerStats.rbi}`,
                  playerStats.runs > 0 && `R:${playerStats.runs}`,
                  playerStats.strikeouts > 0 && `SO:${playerStats.strikeouts}`,
                ].filter(Boolean)
              : []

            return (
              <div key={player.id || idx}>
                <div className="flex items-center justify-between gap-2 px-4 py-1.5 font-vintage text-[13px] text-koshien-chalk transition-colors hover:bg-koshien-green/30">
                  <span className="w-5 flex-shrink-0 text-right font-bold text-koshien-gold">{idx + 1}</span>

                  <span className="min-w-0 flex-shrink-0 px-2 font-bold">{player.name}</span>

                  <span className="flex-shrink-0 font-bold text-koshien-gold">{abh}</span>

                  <div className="ml-auto flex flex-shrink-0 gap-1">
                    {activeStats.map((stat, i) => (
                      <span
                        key={i}
                        className="whitespace-nowrap rounded bg-koshien-green/40 px-1.5 py-0.5 text-[10px] text-koshien-gold/80"
                      >
                        {stat}
                      </span>
                    ))}
                  </div>
                </div>

                {idx < lineup.length - 1 && <div className="border-t border-koshien-gold/10" />}
              </div>
            )
          })
        ) : (
          <div className="flex h-full items-center justify-center py-8 text-center text-[12px] text-koshien-gold/60">
            No lineup data
          </div>
        )}
      </div>
    </div>
  )
}