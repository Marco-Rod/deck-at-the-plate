import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// ============================================================================
// GAME PAGE - Deck at the Plate Gameplay Screen
// Following UI Spec V1: HUD minimalista, oscuro, técnico y orientado a decisión
// ============================================================================

export function GamePage() {
  const [selectedZone, setSelectedZone] = useState<number>(25)
  const [selectedActionCard, setSelectedActionCard] = useState<string | null>(null)
  const [chargePercent, setChargePercent] = useState(0)
  const [isCharging, setIsCharging] = useState(false)
  const [hoveredPitchStat, setHoveredPitchStat] = useState<string | null>(null)
  const [hoveredBatterStat, setHoveredBatterStat] = useState<string | null>(null)

  const mockGame = {
    homeTeam: { name: 'AJOLOTES', shortName: 'AJO' },
    awayTeam: { name: 'LOS ANGELES ANGELS', shortName: 'CPU' },
    innings: [
      { home: 0, away: 0 },
      { home: 0, away: 0 },
      { home: 0, away: 0 },
      { home: 0, away: 0 },
      { home: 0, away: 0 },
    ],
    currentInning: 1,
    isTop: true,
    runs: 0,
    hits: 0,
    errors: 0,
    bases: { first: true, second: false, third: false },
  }

  const mockPitcher = {
    id: 'p1',
    name: 'ASTHIER MIPNO',
    number: 22,
    overall: 52,
    velocity: 82,
    control: 75,
    movement: 39,
    stamina: 80,
    pitchCount: 6,
    maxPitches: 10,
  }

  const mockBatter = {
    id: 'b1',
    name: 'AYMO CHOST3R',
    number: 20,
    overall: 50,
    contact: 79,
    power: 79,
    speed: 75,
  }

  const mockNextBatter = {
    id: 'nb1',
    name: 'NOMBRE',
    number: 21,
    contact: 76,
    power: 68,
    speed: 72,
    vsPitcher: { avg: 0.273, hr: 2 },
  }

  const mockActionCards = [
    {
      id: 'card1',
      name: 'BEETA FOREO',
      cost: '3 4',
      description: '1405 C/A OL EJIS AOIO',
      colorToken: 'red',
      icon: '🔥',
    },
    {
      id: 'card2',
      name: 'FIENGAEO',
      cost: '2 4',
      description: 'Pithsería 1405 OA 5 C CALI 53029',
      colorToken: 'purple',
      icon: '👾',
    },
    {
      id: 'card3',
      name: 'PITENDOT',
      cost: '3 4',
      description: 'Droncheu Tlcromscac del GOM',
      colorToken: 'blue',
      icon: '⚡',
    },
    {
      id: 'card4',
      name: 'TODDO SOKENIA',
      cost: '2 4',
      description: 'Gonjaero cúasma ascodia 98',
      colorToken: 'green',
      icon: '🌿',
    },
  ]

  const handleLanzarMouseDown = () => {
    setIsCharging(true)
    setChargePercent(0)
    const interval = setInterval(() => {
      setChargePercent((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + 2
      })
    }, 20)
  }

  const handleLanzarMouseUp = () => {
    setIsCharging(false)
  }

  return (
    <div className="min-h-screen w-full bg-koshien-dark px-4 py-2 sm:px-4 sm:py-3">
      <AnimatePresence mode="wait">
        <Header homeTeam={mockGame.homeTeam} />
        <Scoreboard
          homeTeam={mockGame.homeTeam}
          awayTeam={mockGame.awayTeam}
          innings={mockGame.innings}
        />
        <GameSituation
          runs={mockGame.runs}
          hits={mockGame.hits}
          errors={mockGame.errors}
          inning={mockGame.currentInning}
          isTop={mockGame.isTop}
          bases={mockGame.bases}
        />
        <CoreGameplay
          pitcher={mockPitcher}
          batter={mockBatter}
          selectedZone={selectedZone}
          setSelectedZone={setSelectedZone}
          hoveredPitchStat={hoveredPitchStat}
          setHoveredPitchStat={setHoveredPitchStat}
          hoveredBatterStat={hoveredBatterStat}
          setHoveredBatterStat={setHoveredBatterStat}
        />
        <NextBatterPreview nextBatter={mockNextBatter} />
        <ActionCardsSection
          cards={mockActionCards}
          selectedCardId={selectedActionCard}
          setSelectedCardId={setSelectedActionCard}
        />
        <LanzarButton
          chargePercent={chargePercent}
          isCharging={isCharging}
          onMouseDown={handleLanzarMouseDown}
          onMouseUp={handleLanzarMouseUp}
          onTouchStart={handleLanzarMouseDown}
          onTouchEnd={handleLanzarMouseUp}
        />
      </AnimatePresence>
    </div>
  )
}

// ============================================================================
// SECTION COMPONENTS
// ============================================================================

interface HeaderProps {
  homeTeam: { name: string; shortName: string }
}

function Header({ homeTeam }: HeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-2 flex items-center justify-between"
    >
      <h1 className="font-sports text-2xl font-bold uppercase tracking-wider text-koshien-chalk sm:text-3xl">
        {homeTeam.shortName} VS CPU
      </h1>
      <motion.button
        whileHover={{ scale: 1.05, borderColor: '#FF554F' }}
        whileTap={{ scale: 0.95 }}
        className="rounded border border-koshien-red bg-koshien-dark px-4 py-2 text-sm font-bold uppercase text-koshien-red transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-red sm:px-6 sm:py-2.5"
        aria-label="Finalizar partida"
      >
        <span className="text-xs sm:text-sm">🎬 FINALIZAR</span>
      </motion.button>
    </motion.div>
  )
}

interface ScoreboardProps {
  homeTeam: { name: string; shortName: string }
  awayTeam: { name: string; shortName: string }
  innings: Array<{ home: number; away: number }>
}

function Scoreboard({ homeTeam, awayTeam, innings }: ScoreboardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="mb-2 border border-koshien-border bg-koshien-dark/40 p-3 sm:p-4"
    >
      <div className="mb-2 grid grid-cols-[1fr_repeat(5,1fr)] gap-2 sm:gap-3">
        <div className="text-xs font-bold uppercase text-koshien-muted sm:text-sm">
          {homeTeam.shortName}
        </div>
        {innings.map((_, idx) => (
          <div
            key={`inning-${idx}`}
            className="text-center font-vintage text-xs font-bold text-koshien-gold sm:text-sm"
          >
            {idx + 1}
          </div>
        ))}
      </div>

      <div className="mb-2 grid grid-cols-[1fr_repeat(5,1fr)] gap-2 border-b border-koshien-border/30 pb-2 sm:gap-3">
        <div className="truncate text-xs font-bold uppercase text-koshien-chalk sm:text-sm">
          {awayTeam.name}
        </div>
        {innings.map((inning, idx) => (
          <motion.div
            key={`away-${idx}`}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: idx * 0.05 }}
            className="text-center font-sports text-sm font-bold text-koshien-chalk sm:text-base"
          >
            {inning.away}
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-[1fr_repeat(5,1fr)] gap-2 sm:gap-3">
        <div className="truncate text-xs font-bold uppercase text-koshien-chalk sm:text-sm">
          {homeTeam.shortName}
        </div>
        {innings.map((inning, idx) => (
          <motion.div
            key={`home-${idx}`}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: idx * 0.05 + 0.25 }}
            className="text-center font-sports text-sm font-bold text-koshien-chalk sm:text-base"
          >
            {inning.home}
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}

interface GameSituationProps {
  runs: number
  hits: number
  errors: number
  inning: number
  isTop: boolean
  bases: { first: boolean; second: boolean; third: boolean }
}

function GameSituation({
  runs,
  hits,
  errors,
  inning,
  isTop,
  bases,
}: GameSituationProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className="mb-2 border border-koshien-border bg-koshien-dark/40 p-3 sm:p-4"
    >
      <div className="grid grid-cols-[auto_1fr_auto] gap-4 sm:gap-6">
        <div className="flex gap-3 sm:gap-4">
          {[
            { label: 'R', value: runs },
            { label: 'H', value: hits },
            { label: 'E', value: errors },
          ].map(({ label, value }) => (
            <motion.div
              key={label}
              whileHover={{ scale: 1.1 }}
              className="text-center"
            >
              <motion.div
                animate={{ scale: value > 0 ? 1.1 : 1 }}
                className="font-sports text-lg font-bold text-koshien-chalk sm:text-2xl"
              >
                {value}
              </motion.div>
              <div className="font-vintage text-[9px] uppercase text-koshien-gold sm:text-xs">
                {label}
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className="flex items-center justify-center"
        >
          <div className="text-center">
            <div className="font-sports text-lg font-bold text-koshien-chalk sm:text-2xl">
              {inning}/3
            </div>
            <div className="font-vintage text-[9px] uppercase text-koshien-gold sm:text-xs">
              {isTop ? 'TOP' : 'BOT'}
            </div>
          </div>
        </motion.div>

        <div className="flex items-center justify-center">
          <BasesDiamond bases={bases} />
        </div>
      </div>
    </motion.div>
  )
}

interface BasesDiamondProps {
  bases: { first: boolean; second: boolean; third: boolean }
}

function BasesDiamond({ bases }: BasesDiamondProps) {
  return (
    <svg viewBox="0 0 60 60" className="h-12 w-12 sm:h-14 sm:w-14">
      <path
        d="M 30 10 L 50 30 L 30 50 L 10 30 Z"
        fill="none"
        stroke="#F2A13A"
        strokeWidth="1"
      />
      <motion.circle
        cx="30"
        cy="10"
        r="2"
        fill={bases.third ? '#F2A13A' : 'none'}
        animate={bases.third ? { r: [2, 3.5, 2] } : {}}
        transition={{ repeat: Infinity, duration: 1 }}
      />
      <motion.circle
        cx="50"
        cy="30"
        r="2"
        fill={bases.first ? '#F2A13A' : 'none'}
        animate={bases.first ? { r: [2, 3.5, 2] } : {}}
        transition={{ repeat: Infinity, duration: 1, delay: 0.2 }}
      />
      <circle cx="30" cy="50" r="2" fill="none" />
      <motion.circle
        cx="10"
        cy="30"
        r="2"
        fill={bases.second ? '#F2A13A' : 'none'}
        animate={bases.second ? { r: [2, 3.5, 2] } : {}}
        transition={{ repeat: Infinity, duration: 1, delay: 0.1 }}
      />
      <circle cx="30" cy="30" r="1.5" fill="#F2A13A" opacity="0.5" />
    </svg>
  )
}

interface CoreGameplayProps {
  pitcher: any
  batter: any
  selectedZone: number
  setSelectedZone: (zone: number) => void
  hoveredPitchStat: string | null
  setHoveredPitchStat: (stat: string | null) => void
  hoveredBatterStat: string | null
  setHoveredBatterStat: (stat: string | null) => void
}

function CoreGameplay({
  pitcher,
  batter,
  selectedZone,
  setSelectedZone,
  hoveredPitchStat,
  setHoveredPitchStat,
  hoveredBatterStat,
  setHoveredBatterStat,
}: CoreGameplayProps) {
  return (
    <div className="mb-2 grid grid-cols-3 gap-2 sm:gap-3">
      <PitcherCard
        pitcher={pitcher}
        hoveredStat={hoveredPitchStat}
        setHoveredStat={setHoveredPitchStat}
      />
      <StrikeZone selectedZone={selectedZone} setSelectedZone={setSelectedZone} />
      <BatterCard
        batter={batter}
        hoveredStat={hoveredBatterStat}
        setHoveredStat={setHoveredBatterStat}
      />
    </div>
  )
}

interface PitcherCardProps {
  pitcher: any
  hoveredStat: string | null
  setHoveredStat: (stat: string | null) => void
}

function PitcherCard({ pitcher, hoveredStat, setHoveredStat }: PitcherCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.3 }}
      className="border border-koshien-purple bg-koshien-dark/60 p-2 sm:p-3"
    >
      <div className="mb-2 flex items-center justify-between border-b border-white/10 pb-1">
        <span className="font-vintage text-[9px] uppercase text-koshien-muted sm:text-xs">
          PITCHER
        </span>
        <span className="font-sports text-xs font-bold text-koshien-gold sm:text-sm">
          {pitcher.overall}
        </span>
      </div>

      <motion.div
        animate={{ scale: 1 }}
        initial={{ scale: 0.8 }}
        className="mb-2 text-center font-sports text-2xl font-bold text-koshien-purple sm:text-3xl"
      >
        #{pitcher.number}
      </motion.div>

      <div className="mb-2 truncate text-center font-vintage text-[10px] font-bold uppercase text-koshien-chalk sm:text-xs">
        {pitcher.name}
      </div>

      <div className="mb-2 grid grid-cols-3 gap-1">
        {[
          { label: 'VEL', value: pitcher.velocity },
          { label: 'CTRL', value: pitcher.control },
          { label: 'MOV', value: pitcher.movement },
        ].map(({ label, value }) => (
          <motion.div
            key={label}
            onMouseEnter={() => setHoveredStat(label)}
            onMouseLeave={() => setHoveredStat(null)}
            whileHover={{ scale: 1.05 }}
            className={`rounded border transition-all ${
              hoveredStat === label
                ? 'border-koshien-purple bg-koshien-purple/10'
                : 'border-koshien-purple/40 bg-koshien-dark'
            } p-1 text-center`}
          >
            <div className="font-vintage text-[8px] uppercase text-koshien-muted sm:text-[9px]">
              {label}
            </div>
            <motion.div
              animate={{ scale: hoveredStat === label ? 1.1 : 1 }}
              className="font-sports text-xs font-bold text-koshien-purple sm:text-sm"
            >
              {value}
            </motion.div>
          </motion.div>
        ))}
      </div>

      <div className="mb-2 border-t border-white/10 pt-1">
        <div className="mb-1 flex items-center justify-between">
          <span className="font-vintage text-[8px] uppercase text-koshien-muted sm:text-[9px]">
            ⚡ STAMINA
          </span>
          <span className="font-sports text-xs font-bold text-koshien-green sm:text-sm">
            {pitcher.stamina}%
          </span>
        </div>
        <div className="h-1 w-full overflow-hidden rounded bg-koshien-dark/50">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pitcher.stamina}%` }}
            transition={{ duration: 0.8 }}
            className="h-full bg-gradient-to-r from-koshien-green to-koshien-orange"
          />
        </div>
      </div>

      <div className="text-center font-vintage text-[8px] uppercase text-koshien-muted sm:text-[9px]">
        ⚾ {pitcher.pitchCount} LANZAMIENTOS
      </div>
    </motion.div>
  )
}

interface StrikeZoneProps {
  selectedZone: number
  setSelectedZone: (zone: number) => void
}

function StrikeZone({ selectedZone, setSelectedZone }: StrikeZoneProps) {
  const zones = [
    [31, 22, 23],
    [24, 25, 26],
    [27, 28, 29],
  ]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.35 }}
      className="border border-koshien-border bg-koshien-dark/60 p-2 sm:p-3"
    >
      <div className="mb-2 text-center font-vintage text-[10px] uppercase text-koshien-gold sm:text-xs">
        ZONA DE STRIKE
      </div>

      <div className="grid grid-cols-3 gap-1">
        {zones.flat().map((zoneNum) => {
          const isSelected = zoneNum === selectedZone
          return (
            <motion.button
              key={zoneNum}
              onClick={() => setSelectedZone(zoneNum)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              layoutId={`zone-${zoneNum}`}
              className={`aspect-square rounded border transition-all focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-koshien-gold ${
                isSelected
                  ? 'border-2 border-koshien-red bg-koshien-red/20 shadow-[0_0_8px_rgba(255,85,79,0.4)]'
                  : 'border border-koshien-grid bg-koshien-dark/40 hover:border-koshien-border'
              }`}
            >
              <span className="font-sports text-xs font-bold text-koshien-chalk sm:text-sm">
                {zoneNum}
              </span>
            </motion.button>
          )
        })}
      </div>
    </motion.div>
  )
}

interface BatterCardProps {
  batter: any
  hoveredStat: string | null
  setHoveredStat: (stat: string | null) => void
}

function BatterCard({ batter, hoveredStat, setHoveredStat }: BatterCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.4 }}
      className="border border-koshien-purple bg-koshien-dark/60 p-2 sm:p-3"
    >
      <div className="mb-2 flex items-center justify-between border-b border-white/10 pb-1">
        <span className="font-vintage text-[9px] uppercase text-koshien-muted sm:text-xs">
          BATTER
        </span>
        <span className="font-sports text-xs font-bold text-koshien-gold sm:text-sm">
          {batter.overall}
        </span>
      </div>

      <motion.div
        animate={{ scale: 1 }}
        initial={{ scale: 0.8 }}
        className="mb-2 text-center font-sports text-2xl font-bold text-koshien-purple sm:text-3xl"
      >
        #{batter.number}
      </motion.div>

      <div className="mb-2 truncate text-center font-vintage text-[10px] font-bold uppercase text-koshien-chalk sm:text-xs">
        {batter.name}
      </div>

      <div className="mb-2 grid grid-cols-3 gap-1">
        {[
          { label: 'CON', value: batter.contact },
          { label: 'PWR', value: batter.power },
          { label: 'SPD', value: batter.speed },
        ].map(({ label, value }) => (
          <motion.div
            key={label}
            onMouseEnter={() => setHoveredStat(label)}
            onMouseLeave={() => setHoveredStat(null)}
            whileHover={{ scale: 1.05 }}
            className={`rounded border transition-all ${
              hoveredStat === label
                ? 'border-koshien-purple bg-koshien-purple/10'
                : 'border-koshien-purple/40 bg-koshien-dark'
            } p-1 text-center`}
          >
            <div className="font-vintage text-[8px] uppercase text-koshien-muted sm:text-[9px]">
              {label}
            </div>
            <motion.div
              animate={{ scale: hoveredStat === label ? 1.1 : 1 }}
              className="font-sports text-xs font-bold text-koshien-purple sm:text-sm"
            >
              {value}
            </motion.div>
          </motion.div>
        ))}
      </div>

      <div className="flex-1" />
    </motion.div>
  )
}

interface NextBatterPreviewProps {
  nextBatter: any
}

function NextBatterPreview({ nextBatter }: NextBatterPreviewProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.45 }}
      className="mb-2 border border-koshien-green/30 bg-koshien-dark/40 p-2 sm:p-3"
    >
      <div className="flex flex-col gap-1 sm:gap-2">
        <div className="flex items-center justify-between">
          <span className="font-vintage text-[9px] uppercase text-koshien-green sm:text-xs">
            SIGUIENTE BATEADOR
          </span>
          <motion.span
            animate={{ x: [0, 3, 0] }}
            transition={{ repeat: Infinity, duration: 1 }}
            className="text-xs text-koshien-green"
          >
            ▶
          </motion.span>
        </div>

        <div className="flex items-baseline gap-1">
          <span className="font-sports font-bold text-koshien-gold sm:text-sm">
            #{nextBatter.number}
          </span>
          <span className="truncate font-vintage text-xs font-bold uppercase text-koshien-chalk sm:text-sm">
            {nextBatter.name}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 sm:gap-3">
          {[
            { label: 'CON', value: nextBatter.contact },
            { label: 'PWR', value: nextBatter.power },
            { label: 'SPD', value: nextBatter.speed },
          ].map(({ label, value }) => (
            <motion.div
              key={label}
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="font-vintage text-[8px] uppercase text-koshien-muted sm:text-[9px]">
                {label}
              </div>
              <div className="font-sports text-xs font-bold text-koshien-green sm:text-sm">
                {value}
              </div>
            </motion.div>
          ))}
        </div>

        <div className="border-t border-koshien-green/20 pt-1 text-center font-vintage text-[8px] uppercase text-koshien-green sm:text-[9px]">
          VS P: .{(nextBatter.vsPitcher.avg * 1000).toFixed(0)} {nextBatter.vsPitcher.hr}HR
        </div>
      </div>
    </motion.div>
  )
}

interface ActionCardsSectionProps {
  cards: any[]
  selectedCardId: string | null
  setSelectedCardId: (id: string | null) => void
}

function ActionCardsSection({
  cards,
  selectedCardId,
  setSelectedCardId,
}: ActionCardsSectionProps) {
  const colorMap: Record<string, string> = {
    red: 'border-koshien-red',
    purple: 'border-koshien-purple',
    blue: 'border-blue-400',
    green: 'border-koshien-green',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.5 }}
      className="mb-3 border border-koshien-border bg-koshien-dark/40 p-2 sm:p-3"
    >
      <div className="mb-2 text-center font-vintage text-xs uppercase text-koshien-gold sm:text-sm">
        CARTAS DE ACCIÓN
      </div>

      <div className="grid grid-cols-4 gap-1 sm:gap-2">
        {cards.map((card, idx) => {
          const isSelected = card.id === selectedCardId
          const borderColor = colorMap[card.colorToken] || 'border-koshien-border'

          return (
            <motion.button
              key={card.id}
              onClick={() => setSelectedCardId(isSelected ? null : card.id)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05 + 0.5 }}
              className={`flex flex-col items-center justify-center rounded border p-1.5 text-center transition-all focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-koshien-gold sm:p-2 ${
                isSelected
                  ? `${borderColor} border-2 bg-koshien-dark/80 shadow-[0_0_12px_rgba(255,85,79,0.3)]`
                  : `${borderColor} border bg-koshien-dark/40 hover:bg-koshien-dark/60`
              }`}
            >
              <motion.div
                animate={{ scale: isSelected ? 1.2 : 1 }}
                className="mb-1 text-lg sm:text-2xl"
              >
                {card.icon}
              </motion.div>

              <div className="mb-0.5 font-vintage text-[7px] font-bold uppercase text-koshien-chalk sm:text-[8px]">
                {card.name}
              </div>

              <div className="font-vintage text-[7px] text-koshien-muted sm:text-[8px]">
                {card.cost}
              </div>
            </motion.button>
          )
        })}
      </div>
    </motion.div>
  )
}

interface LanzarButtonProps {
  chargePercent: number
  isCharging: boolean
  onMouseDown: () => void
  onMouseUp: () => void
  onTouchStart: () => void
  onTouchEnd: () => void
}

function LanzarButton({
  chargePercent,
  isCharging,
  onMouseDown,
  onMouseUp,
  onTouchStart,
  onTouchEnd,
}: LanzarButtonProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.65 }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 transform sm:relative sm:bottom-auto sm:left-auto sm:translate-x-0"
    >
      <div className="flex flex-col items-center gap-2">
        <motion.button
          onMouseDown={onMouseDown}
          onMouseUp={onMouseUp}
          onTouchStart={onTouchStart}
          onTouchEnd={onTouchEnd}
          whileHover={{ scale: isCharging ? 1 : 1.05 }}
          whileTap={{ scale: 0.98 }}
          className={`relative flex min-h-[64px] min-w-[150px] flex-col items-center justify-center rounded border-2 border-koshien-orange text-center font-sports text-2xl font-bold uppercase tracking-wider text-koshien-chalk transition-all sm:min-h-[78px] sm:min-w-[190px] sm:text-3xl ${
            isCharging
              ? 'bg-koshien-orange/20 shadow-[0_0_20px_rgba(242,161,58,0.6)]'
              : 'bg-koshien-dark/80 shadow-[0_0_12px_rgba(242,161,58,0.3)] hover:shadow-[0_0_16px_rgba(242,161,58,0.5)]'
          }`}
        >
          {isCharging && (
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${chargePercent}%` }}
              className="absolute inset-0 z-0 rounded bg-koshien-orange/30"
            />
          )}

          <div className="relative z-10 flex flex-col items-center gap-0.5">
            <span>🔥 LANZAR</span>
          </div>
        </motion.button>

        <span className="font-vintage text-[9px] uppercase text-koshien-orange sm:text-xs">
          {isCharging ? `${Math.round(chargePercent)}%` : 'MANTÉN PARA CARGAR'}
        </span>
      </div>
    </motion.div>
  )
}
