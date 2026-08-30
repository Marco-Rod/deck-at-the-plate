import type { BatterStats } from '@/shared/api/types'
import { LineupPanel } from './LineupPanel'
import type { LineupPlayer } from './LineupPanel'
import { StrikeoutCounter } from './StrikeoutCounter'

interface GameStatsPanelProps {
  lineup: LineupPlayer[]
  stats: Record<string, BatterStats>
  isPitcher: boolean
  pitcherStrikeouts?: number
  pitcherName?: string
  animateStrikeout?: boolean
}

export function GameStatsPanel({
  lineup,
  stats,
  isPitcher,
  pitcherStrikeouts = 0,
  pitcherName = 'Pitcher',
  animateStrikeout = false,
}: GameStatsPanelProps) {
  if (isPitcher) {
    return (
      <StrikeoutCounter
        strikeouts={pitcherStrikeouts}
        pitcherName={pitcherName}
        animate={animateStrikeout}
      />
    )
  }

  return <LineupPanel lineup={lineup} stats={stats} />
}