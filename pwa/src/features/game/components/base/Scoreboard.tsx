import type { GameStateWS } from '@/shared/api/types'

interface ScoreboardProps {
  gameState?: GameStateWS | null
  homeTeamName: string
  awayTeamName: string
  totalInnings?: number
  homeHits?: number
  awayHits?: number
  inningRuns?: Record<string, number>
  compact?: boolean
}

export function Scoreboard({
  gameState,
  homeTeamName,
  awayTeamName,
  totalInnings = 9,
  homeHits = 0,
  awayHits = 0,
  inningRuns = {},
  compact = false,
}: ScoreboardProps) {
  const homeScore = gameState?.homeScore ?? 0
  const awayScore = gameState?.awayScore ?? 0
  const currentInning = gameState?.currentInning ?? 1
  const displayInnings = compact ? Math.min(5, totalInnings) : totalInnings

  const inningHeaderSize = compact ? 'text-[8px]' : 'text-[9px] sm:text-[10px] md:text-[11px]'
  const inningDataSize = compact ? 'text-[11px]' : 'text-[11px] sm:text-[12px] md:text-[14px]'
  const teamNameSize = compact ? 'text-[9px]' : 'text-[10px] sm:text-[11px] md:text-[13px]'
  const scoreSize = compact ? 'text-[13px]' : 'text-[14px] sm:text-[16px] md:text-[18px]'
  const teamNameWidth = compact ? 'w-28' : 'w-32 sm:w-40 md:w-60'
  const inningColWidth = compact ? 'w-5' : 'w-6 sm:w-7 md:w-9'
  const totalColWidth = compact ? 'w-7' : 'w-8 sm:w-9 md:w-11'

  return (
    <div className="w-full overflow-x-auto rounded-sm border border-koshien-gold/30 bg-koshien-dark/90">
      {/* HEADER ROW */}
      <div className="flex min-w-max items-center border-b border-koshien-gold/20 bg-koshien-dark px-2 py-1 md:px-4 md:py-2">
        <div className={`${teamNameWidth} flex-shrink-0 text-left`}>
          <span className={`font-vintage ${inningHeaderSize} font-bold uppercase tracking-wider text-koshien-gold`}>
            {compact ? 'INN' : 'INNING'}
          </span>
        </div>

        <div className="flex flex-1 gap-0.5 sm:gap-1 md:gap-3">
          {Array.from({ length: displayInnings }).map((_, idx) => (
            <div key={`header-inning-${idx + 1}`} className={`${inningColWidth} flex-shrink-0 text-center`}>
              <span className={`font-vintage ${inningHeaderSize} font-bold text-koshien-cream`}>{idx + 1}</span>
            </div>
          ))}
        </div>

        <div className="ml-1 flex flex-shrink-0 gap-0.5 sm:ml-2 sm:gap-2 md:ml-4 md:gap-4">
          {['R', 'H', 'E'].map((col) => (
            <div key={col} className={`${totalColWidth} text-center`}>
              <span className={`font-vintage ${inningHeaderSize} font-bold text-koshien-cream`}>{col}</span>
            </div>
          ))}
        </div>
      </div>

      {/* AWAY TEAM ROW */}
      <div className="flex min-w-max items-center border-b border-koshien-gold/10 bg-koshien-green/30 px-2 py-1 md:px-4 md:py-2">
        <div className={`${teamNameWidth} flex-shrink-0 truncate`}>
          <span className={`font-vintage ${teamNameSize} font-bold uppercase tracking-wider text-koshien-chalk`}>
            {compact ? awayTeamName.substring(0, 4) : awayTeamName}
          </span>
        </div>

        <div className="flex flex-1 gap-0.5 sm:gap-1 md:gap-3">
          {Array.from({ length: displayInnings }).map((_, idx) => {
            const inning = idx + 1
            const displayRuns = inningRuns?.[`${inning}_true`] ?? 0
            const showRuns = inning <= currentInning ? displayRuns : ''

            return (
              <div key={`away-inning-${inning}`} className={`${inningColWidth} flex-shrink-0 text-center`}>
                <span className={`font-vintage ${inningDataSize} font-bold text-koshien-gold`}>{showRuns}</span>
              </div>
            )
          })}
        </div>

        <div className="ml-1 flex flex-shrink-0 gap-0.5 sm:ml-2 sm:gap-2 md:ml-4 md:gap-4">
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-vintage ${scoreSize} font-bold text-koshien-chalk`}>{awayScore}</span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-vintage ${inningDataSize} font-bold text-koshien-chalk`}>{awayHits}</span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-vintage ${inningDataSize} font-bold text-koshien-chalk`}>0</span>
          </div>
        </div>
      </div>

      {/* HOME TEAM ROW */}
      <div className="flex min-w-max items-center border-b border-koshien-gold/10 bg-koshien-dark px-2 py-1 md:px-4 md:py-2">
        <div className={`${teamNameWidth} flex-shrink-0 truncate`}>
          <span className={`font-vintage ${teamNameSize} font-bold uppercase tracking-wider text-koshien-chalk`}>
            {compact ? homeTeamName.substring(0, 4) : homeTeamName}
          </span>
        </div>

        <div className="flex flex-1 gap-0.5 sm:gap-1 md:gap-3">
          {Array.from({ length: displayInnings }).map((_, idx) => {
            const inning = idx + 1
            const displayRuns = inningRuns?.[`${inning}_false`] ?? 0
            const showRuns = inning <= currentInning ? displayRuns : ''

            return (
              <div key={`home-inning-${inning}`} className={`${inningColWidth} flex-shrink-0 text-center`}>
                <span className={`font-vintage ${inningDataSize} font-bold text-koshien-gold`}>{showRuns}</span>
              </div>
            )
          })}
        </div>

        <div className="ml-1 flex flex-shrink-0 gap-0.5 sm:ml-2 sm:gap-2 md:ml-4 md:gap-4">
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-vintage ${scoreSize} font-bold text-koshien-chalk`}>{homeScore}</span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-vintage ${inningDataSize} font-bold text-koshien-chalk`}>{homeHits}</span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-vintage ${inningDataSize} font-bold text-koshien-chalk`}>0</span>
          </div>
        </div>
      </div>
    </div>
  )
}