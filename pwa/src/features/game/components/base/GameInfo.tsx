import type { GameRunners } from '@/shared/api/types'

interface GameInfoProps {
  balls: number
  strikes: number
  outs: number
  currentInning: number
  totalInnings: number
  isTopInning: boolean
  runners: GameRunners
}

export function GameInfo({
  balls,
  strikes,
  outs,
  currentInning,
  totalInnings,
  isTopInning,
  runners,
}: GameInfoProps) {
  return (
    <div className="w-full rounded-sm border border-koshien-gold/40 bg-koshien-dark/95 p-3">
      <div className="flex h-20 items-center justify-between gap-8">
        {/* LEFT: BALLS / STRIKES / OUTS */}
        <div className="flex gap-8">
          <div className="min-w-fit text-center">
            <div className="font-sports text-3xl font-bold leading-tight text-koshien-chalk">{balls}</div>
            <div className="font-vintage mt-1 text-[8px] font-bold uppercase tracking-wider text-koshien-gold">B</div>
          </div>

          <div className="min-w-fit text-center">
            <div className="font-sports text-3xl font-bold leading-tight text-koshien-chalk">{strikes}</div>
            <div className="font-vintage mt-1 text-[8px] font-bold uppercase tracking-wider text-koshien-gold">S</div>
          </div>

          <div className="min-w-fit text-center">
            <div className="font-sports text-3xl font-bold leading-tight text-koshien-chalk">{outs}</div>
            <div className="font-vintage mt-1 text-[8px] font-bold uppercase tracking-wider text-koshien-gold">O</div>
          </div>
        </div>

        {/* CENTER: INNING INFO */}
        <div className="flex-1 text-center">
          <div className="font-vintage text-[12px] font-bold uppercase tracking-wider text-koshien-cream">
            {currentInning}/{totalInnings}
          </div>
          <div className="font-vintage mt-1 text-[11px] font-bold uppercase text-koshien-gold">
            {isTopInning ? 'TOP' : 'BOT'}
          </div>
        </div>

        {/* RIGHT: BASES DIAMOND */}
        <div className="ml-auto flex items-center justify-end">
          <div className="flex flex-col items-center gap-1">
            <div className="flex justify-center">
              <div
                className={`h-5 w-5 rotate-45 border-2 transition-colors ${
                  runners.b2 ? 'border-koshien-gold bg-koshien-gold/40' : 'border-koshien-gold/40 bg-transparent'
                }`}
              />
            </div>

            <div className="flex items-center justify-center gap-3">
              <div
                className={`h-5 w-5 rotate-45 border-2 transition-colors ${
                  runners.b3 ? 'border-koshien-gold bg-koshien-gold/40' : 'border-koshien-gold/40 bg-transparent'
                }`}
              />
              <div className="h-3 w-3 rounded-sm border border-koshien-gold/60 bg-koshien-gold/20" />
              <div
                className={`h-5 w-5 rotate-45 border-2 transition-colors ${
                  runners.b1 ? 'border-koshien-gold bg-koshien-gold/40' : 'border-koshien-gold/40 bg-transparent'
                }`}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}