# 🛠️ Responsive Design - Detailed Implementation Guide

**Purpose**: Code examples and exact changes needed for each screen component  
**Language**: TypeScript/TSX + Tailwind CSS  
**Status**: Planning - Ready for implementation

---

## 📋 Quick Reference: File Locations & Priorities

```
CRITICAL (must do):
├── StadiumShowcaseScreen.tsx (gameplay main layout) - 6 hours
├── Scoreboard.tsx (game score display) - 3 hours
├── PlayerCard.tsx (player display) - 2 hours
└── LobbyScreen.jsx (main menu) - 5 hours

HIGH (important):
├── RosterSelectionScreen.jsx (lineup picker) - 6 hours
├── OnboardingScreen.jsx (franchise selection) - 4 hours
└── GameplayDeckAndReveal.tsx (card reveal) - 2 hours

MEDIUM (nice to have):
├── MyTeamScreen.jsx (team management) - 5 hours
└── CardShowcaseScreen.jsx (card album) - 5 hours
```

---

## 🔴 CRITICAL FIX #1: StadiumShowcaseScreen Main Layout

**File**: `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  
**Line**: ~698  
**Severity**: 🔴 CRITICAL  
**Effort**: 6 hours  
**Impact**: Entire gameplay screen responsive

### Current Code (Broken):
```tsx
<main className="w-[95%] mx-auto flex justify-between items-center min-h-[500px]">
  {/* LEFT PANEL: 450px fixed */}
  <div className="w-[450px] flex-shrink-0">
    <LineupPanel ... />
    <GameInfo ... />
  </div>

  {/* CENTER: Field and gameplay */}
  <CentralField ... />

  {/* RIGHT PANEL: 450px fixed */}
  <div className="w-[450px] flex-shrink-0">
    <PitcherPanel ... />
  </div>
</main>
```

### Fixed Code:
```tsx
<main className="w-[95%] md:w-full mx-auto flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 md:gap-6 min-h-auto md:min-h-[500px] overflow-x-hidden">
  {/* LEFT PANEL: Full width on mobile, 450px on desktop */}
  <div className="w-full lg:w-[450px] lg:flex-shrink-0 overflow-y-auto max-h-[400px] md:max-h-full">
    <LineupPanel responsive compact={isMobile} />
    <GameInfo responsive />
  </div>

  {/* CENTER: Full width on mobile, flexible on desktop */}
  <div className="w-full lg:flex-1 order-3 lg:order-2">
    <CentralField responsive scale={isMobile ? 0.85 : 1} />
  </div>

  {/* RIGHT PANEL: Full width on mobile, 450px on desktop */}
  <div className="w-full lg:w-[450px] lg:flex-shrink-0 overflow-y-auto max-h-[400px] md:max-h-full order-2 lg:order-3">
    <PitcherPanel responsive />
  </div>
</main>
```

### Key Changes:
```tsx
// BEFORE
flex justify-between items-center
w-[450px] flex-shrink-0

// AFTER
flex flex-col lg:flex-row  // Stack on mobile, 3-col on desktop
justify-between items-start lg:items-center  // Align to top on mobile
gap-4 md:gap-6  // Responsive spacing
w-full lg:w-[450px]  // Full width mobile, 450px desktop
overflow-y-auto max-h-[400px] md:max-h-full  // Scrollable on mobile
order-2 lg:order-3  // Reorder on desktop
```

### Related Components Need Updates:
- ✅ `CentralField.tsx` - Add responsive prop
- ✅ `LineupPanel.tsx` - Add responsive prop
- ✅ `GameInfo.tsx` - Add responsive prop (if separate)
- ✅ `PitcherPanel.tsx` - Add responsive prop (if separate)

---

## 🔴 CRITICAL FIX #2: Scoreboard Component

**File**: `frontend/src/components/stadium/components/base/Scoreboard.tsx`  
**Line**: ~93-136  
**Severity**: 🔴 CRITICAL  
**Effort**: 3 hours  
**Impact**: Game score readability on all devices

### Current Code (Broken):
```tsx
export const Scoreboard: React.FC<ScoreboardProps> = ({
  gameState,
  homeTeamName,
  awayTeamName,
  totalInnings = 9,
  homeHits = 0,
  awayHits = 0,
  inningRuns = {},
}) => {
  // ...
  return (
    <div className="w-full bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded-sm overflow-hidden">
      {/* HEADER ROW */}
      <div className="flex items-center bg-[#0A0D0F] border-b border-[#C5A059]/20 px-4 py-2">
        {/* INNING label - LARGER */}
        <div className="w-60 text-left">
          <span className="font-mono text-[11px] text-[#C5A059] uppercase font-bold tracking-wider">
            INNING
          </span>
        </div>

        {/* Inning columns (1-9) */}
        <div className="flex gap-3 flex-1">
          {Array.from({ length: totalInnings }).map((_, idx) => (
            <div className="w-9 text-center">
              <span className="font-mono text-[10px] text-[#E6DFD3] font-bold">
                {idx + 1}
              </span>
            </div>
          ))}
        </div>
      </div>
```

### Fixed Code:
```tsx
interface ScoreboardProps {
  gameState?: GameState;
  userRole?: string;
  homeTeamName: string;
  awayTeamName: string;
  totalInnings?: number;
  homeHits?: number;
  awayHits?: number;
  inningRuns?: Record<string, number>;
  responsive?: boolean;  // NEW: Enable responsive mode
  compact?: boolean;     // NEW: Ultra-compact for mobile
}

export const Scoreboard: React.FC<ScoreboardProps> = ({
  gameState,
  homeTeamName,
  awayTeamName,
  totalInnings = 9,
  homeHits = 0,
  awayHits = 0,
  inningRuns = {},
  responsive = true,
  compact = false,
}) => {
  const homeScore = gameState?.homeScore ?? 0;
  const awayScore = gameState?.awayScore ?? 0;
  const isTopInning = gameState?.isTopInning ?? true;
  const currentInning = gameState?.currentInning ?? 1;

  // Determine display mode
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const displayInnings = compact ? Math.min(5, totalInnings) : totalInnings;
  
  // Dynamic font sizes
  const inningHeaderSize = compact ? 'text-[8px]' : 'text-[10px] md:text-[11px]';
  const inningDataSize = compact ? 'text-[11px]' : 'text-[12px] md:text-[14px]';
  const teamNameSize = compact ? 'text-[10px]' : 'text-[11px] md:text-[13px]';
  const totalSize = compact ? 'text-[13px]' : 'text-[14px] md:text-[18px]';
  const scoreSize = compact ? 'text-[14px]' : 'text-[16px] md:text-[18px]';

  // Dynamic widths
  const teamNameWidth = compact ? 'w-32' : 'w-40 md:w-60';
  const inningColWidth = compact ? 'w-6' : 'w-7 md:w-9';
  const totalColWidth = compact ? 'w-8' : 'w-9 md:w-11';

  return (
    <div className="w-full bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded-sm overflow-x-auto">
      {/* HEADER ROW */}
      <div className="flex items-center bg-[#0A0D0F] border-b border-[#C5A059]/20 px-2 md:px-4 py-1 md:py-2 min-w-max">
        {/* INNING label */}
        <div className={`${teamNameWidth} text-left flex-shrink-0`}>
          <span className={`font-mono ${inningHeaderSize} text-[#C5A059] uppercase font-bold tracking-wider`}>
            INN
          </span>
        </div>

        {/* Inning columns (1-9 or 1-5) */}
        <div className="flex gap-1 md:gap-3 flex-1">
          {Array.from({ length: displayInnings }).map((_, idx) => (
            <div key={`header-inning-${idx + 1}`} className={`${inningColWidth} text-center flex-shrink-0`}>
              <span className={`font-mono ${inningHeaderSize} text-[#E6DFD3] font-bold`}>
                {idx + 1}
              </span>
            </div>
          ))}
        </div>

        {/* R H E columns */}
        <div className="flex gap-1 md:gap-4 ml-1 md:ml-4 flex-shrink-0">
          {['R', 'H', 'E'].map((col) => (
            <div key={col} className={`${totalColWidth} text-center`}>
              <span className={`font-mono ${inningHeaderSize} text-[#E6DFD3] font-bold`}>
                {col}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* AWAY TEAM ROW */}
      <div className="flex items-center px-2 md:px-4 py-1 md:py-2 bg-[#1A3323]/30 border-b border-[#C5A059]/10 min-w-max">
        {/* Team name */}
        <div className={`${teamNameWidth} truncate flex-shrink-0`}>
          <span className={`font-mono ${teamNameSize} text-[#F7F5F0] uppercase font-bold tracking-wider`}>
            {compact ? awayTeamName.substring(0, 5) : awayTeamName}
          </span>
        </div>

        {/* Inning runs */}
        <div className="flex gap-1 md:gap-3 flex-1">
          {Array.from({ length: displayInnings }).map((_, idx) => {
            const inning = idx + 1;
            const runsKeyTop = `${inning}_true`;
            const displayRuns = inningRuns?.[runsKeyTop] ?? 0;
            const hasEntryBeenPlayed = inning <= currentInning;
            const showRuns = hasEntryBeenPlayed ? displayRuns : '';

            return (
              <div key={`away-inning-${inning}`} className={`${inningColWidth} text-center flex-shrink-0`}>
                <span className={`font-mono ${inningDataSize} text-[#C5A059] font-bold`}>
                  {showRuns}
                </span>
              </div>
            );
          })}
        </div>

        {/* Totals: R H E */}
        <div className="flex gap-1 md:gap-4 ml-1 md:ml-4 flex-shrink-0">
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${scoreSize} text-[#F7F5F0] font-bold`}>
              {awayScore}
            </span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${inningDataSize} text-[#F7F5F0] font-bold`}>
              {awayHits}
            </span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${inningDataSize} text-[#F7F5F0] font-bold`}>
              0
            </span>
          </div>
        </div>
      </div>

      {/* HOME TEAM ROW */}
      <div className="flex items-center px-2 md:px-4 py-1 md:py-2 bg-[#0A0D0F] border-b border-[#C5A059]/10 min-w-max">
        {/* Team name */}
        <div className={`${teamNameWidth} truncate flex-shrink-0`}>
          <span className={`font-mono ${teamNameSize} text-[#F7F5F0] uppercase font-bold tracking-wider`}>
            {compact ? homeTeamName.substring(0, 5) : homeTeamName}
          </span>
        </div>

        {/* Inning runs */}
        <div className="flex gap-1 md:gap-3 flex-1">
          {Array.from({ length: displayInnings }).map((_, idx) => {
            const inning = idx + 1;
            const runsKeyBot = `${inning}_false`;
            const displayRuns = inningRuns?.[runsKeyBot] ?? 0;
            const hasEntryBeenPlayed = inning <= currentInning;
            const showRuns = hasEntryBeenPlayed ? displayRuns : '';

            return (
              <div key={`home-inning-${inning}`} className={`${inningColWidth} text-center flex-shrink-0`}>
                <span className={`font-mono ${inningDataSize} text-[#C5A059] font-bold`}>
                  {showRuns}
                </span>
              </div>
            );
          })}
        </div>

        {/* Totals: R H E */}
        <div className="flex gap-1 md:gap-4 ml-1 md:ml-4 flex-shrink-0">
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${scoreSize} text-[#F7F5F0] font-bold`}>
              {homeScore}
            </span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${inningDataSize} text-[#F7F5F0] font-bold`}>
              {homeHits}
            </span>
          </div>
          <div className={`${totalColWidth} text-center`}>
            <span className={`font-mono ${inningDataSize} text-[#F7F5F0] font-bold`}>
              0
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
```

### Key Changes:
1. ✅ Added `responsive` and `compact` props
2. ✅ Dynamic font sizing based on viewport
3. ✅ Dynamic column widths
4. ✅ Changed from `gap-3` → `gap-1 md:gap-3`
5. ✅ Changed widths to responsive: `w-60` → `w-40 md:w-60`
6. ✅ Added `overflow-x-auto` for horizontal scroll on mobile
7. ✅ Added `min-w-max` to prevent flex shrinking
8. ✅ Responsive padding: `px-4 py-2` → `px-2 md:px-4 py-1 md:py-2`
9. ✅ Team name truncation for mobile
10. ✅ Optional inning reduction for ultra-mobile (show 1-5 instead of 1-9)

---

## 🟠 HIGH FIX #3: PlayerCard Component

**File**: `frontend/src/components/stadium/PlayerCard.tsx`  
**Line**: ~111-221  
**Severity**: 🔴 CRITICAL  
**Effort**: 2-3 hours  
**Impact**: Player card readability across all viewports

### Current Code (Broken):
```tsx
<div className="w-56 h-80 bg-gradient-to-b from-[#1a1a2e] to-[#0f0f1e] border border-[#C5A059]/50 rounded-lg p-3 flex flex-col justify-between">
  {/* Jersey number */}
  <div className="text-center">
    <span className="font-bold text-5xl text-[#C5A059]">
      {playerCard?.number || '?'}
    </span>
  </div>

  {/* Player name */}
  <div className="text-center">
    <p className="text-[10px] text-[#E6DFD3] font-semibold truncate">
      {playerCard?.name}
    </p>
  </div>

  {/* Stats (CRITICAL: 5px is unreadable!) */}
  <div className="grid grid-cols-3 gap-1 text-center">
    {statsArray.map((stat, idx) => (
      <div key={idx}>
        <span className="text-[5px] text-[#C5A059] font-bold">
          {stat.label}
        </span>
        <span className="text-[5px] text-[#E6DFD3]">
          {stat.value}
        </span>
      </div>
    ))}
  </div>

  {/* Team name */}
  <p className="text-[8px] text-[#999999] text-center truncate">
    {playerCard?.team?.name || 'UNKNOWN'}
  </p>
</div>
```

### Fixed Code:
```tsx
interface PlayerCardProps {
  playerCard: PlayerCardType | null;
  responsive?: boolean;
  compact?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const PlayerCard: React.FC<PlayerCardProps> = ({
  playerCard,
  responsive = true,
  compact = false,
  size = 'md',
}) => {
  // Responsive sizing
  const cardWidthClass = {
    sm: 'w-full sm:w-40 md:w-48',
    md: 'w-full sm:w-48 md:w-56',
    lg: 'w-full sm:w-56 md:w-64',
  }[size];

  const jerseySize = {
    sm: 'text-3xl sm:text-4xl md:text-5xl',
    md: 'text-4xl sm:text-5xl md:text-6xl',
    lg: 'text-5xl sm:text-6xl md:text-7xl',
  }[size];

  const statLabelSize = {
    sm: 'text-[6px] sm:text-[7px] md:text-[8px]',
    md: 'text-[8px] sm:text-[9px] md:text-[10px]',
    lg: 'text-[9px] sm:text-[10px] md:text-[11px]',
  }[size];

  const playerNameSize = {
    sm: 'text-[8px] sm:text-[9px] md:text-[10px]',
    md: 'text-[9px] sm:text-[10px] md:text-[11px]',
    lg: 'text-[10px] sm:text-[11px] md:text-[13px]',
  }[size];

  const teamNameSize = {
    sm: 'text-[6px] sm:text-[7px] md:text-[8px]',
    md: 'text-[7px] sm:text-[8px] md:text-[9px]',
    lg: 'text-[8px] sm:text-[9px] md:text-[10px]',
  }[size];

  return (
    <div className={`${cardWidthClass} aspect-[3/4] bg-gradient-to-b from-[#1a1a2e] to-[#0f0f1e] border border-[#C5A059]/50 rounded-lg p-2 sm:p-3 md:p-4 flex flex-col justify-between`}>
      {/* Jersey number */}
      <div className="text-center flex-shrink-0">
        <span className={`font-bold ${jerseySize} text-[#C5A059]`}>
          {playerCard?.number || '?'}
        </span>
      </div>

      {/* Tier badge */}
      <div className="flex justify-center gap-1 flex-wrap">
        {/* Tier indicators - responsive size */}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-0.5 sm:gap-1 text-center flex-1 overflow-hidden">
        {statsArray.map((stat, idx) => (
          <div key={idx} className="flex flex-col justify-center">
            <span className={`${statLabelSize} text-[#C5A059] font-bold truncate`}>
              {stat.label}
            </span>
            <span className={`${statLabelSize} text-[#E6DFD3]`}>
              {stat.value}
            </span>
          </div>
        ))}
      </div>

      {/* Player name */}
      <p className={`${playerNameSize} text-[#E6DFD3] font-semibold truncate`}>
        {playerCard?.name}
      </p>

      {/* Team name */}
      <p className={`${teamNameSize} text-[#999999] text-center truncate`}>
        {playerCard?.team?.name || 'UNKNOWN'}
      </p>
    </div>
  );
};
```

### Key Changes:
1. ✅ Width: `w-56` → `w-full sm:w-48 md:w-56`
2. ✅ Height: `h-80` → `aspect-[3/4]` (maintains ratio on all sizes)
3. ✅ Jersey size: `text-5xl` → `text-3xl sm:text-4xl md:text-5xl`
4. ✅ Stats size: `text-[5px]` → `text-[6px] sm:text-[7px] md:text-[8px]` (minimum 6px, readable)
5. ✅ Player name: `text-[10px]` → `text-[8px] sm:text-[9px] md:text-[10px]`
6. ✅ Team name: `text-[8px]` → `text-[7px] sm:text-[8px] md:text-[9px]`
7. ✅ Padding: `p-3` → `p-2 sm:p-3 md:p-4`
8. ✅ Added `size` prop for different card sizes
9. ✅ Added `aspect-ratio` for responsive height
10. ✅ Gap scaling: `gap-1` → `gap-0.5 sm:gap-1`

---

## 🟠 HIGH FIX #4: LobbyScreen (Main Menu)

**File**: `frontend/src/pages/LobbyScreen.jsx`  
**Severity**: 🟠 HIGH  
**Effort**: 5 hours  
**Impact**: Main entry point usability

### Pattern Changes:
```jsx
// FROM: Fixed grid
<div className="grid grid-cols-3 gap-4 w-max">

// TO: Responsive grid
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 sm:gap-3 md:gap-4 w-full">

// FROM: Fixed button sizes
<button className="w-80 h-24">

// TO: Responsive button sizes
<button className="w-full sm:w-72 md:w-80 h-20 sm:h-24 md:h-28">

// FROM: Fixed navigation layout
<div className="flex gap-4">

// TO: Responsive navigation
<div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
```

---

## 🟠 HIGH FIX #5: RosterSelectionScreen (Lineup Picker)

**File**: `frontend/src/pages/RosterSelectionScreen.jsx`  
**Severity**: 🔴 CRITICAL  
**Effort**: 6 hours  
**Impact**: Core gameplay feature

### Key Changes:
```jsx
// FROM: 3-column fixed layout impossible on mobile
<main className="flex">
  <left className="w-96">
  <center className="flex-1">
  <right className="w-96">

// TO: Stack on mobile, 3-col on desktop
<main className="flex flex-col md:flex-col lg:flex-row gap-4">
  <left className="w-full lg:w-96 h-auto lg:h-full overflow-y-auto">
  <center className="w-full lg:flex-1 h-auto">
  <right className="w-full lg:w-96 h-auto lg:h-full overflow-y-auto">

// Player cards responsive
{/* FROM */}
<div className="w-56 h-80">

{/* TO */}
<div className="w-full sm:w-48 md:w-56 lg:w-64 aspect-[3/4]">

// Field grid responsive scaling
<div style={{ transform: `scale(${isMobile ? 0.75 : 1})` }}>
  {/* Field elements */}
</div>
```

---

## 🟠 MEDIUM FIX #6: CentralField Component

**File**: `frontend/src/components/stadium/components/layouts/CentralField.tsx`  
**Line**: ~47  
**Severity**: 🟡 MEDIUM-HIGH  
**Effort**: 2-3 hours

### Current Code (Broken):
```tsx
<div style={{ width: 'calc(224px + 24px + 144px + 24px + 224px)' }}>
  {/* GameInfo + CentralGameArea + Stats */}
</div>
```

### Fixed Code:
```tsx
<div className="w-full lg:auto flex flex-col lg:flex-row gap-4 lg:gap-6">
  {/* Pitcher card */}
  <div className="w-full sm:w-1/2 lg:w-auto flex-shrink-0">
    <GameInfo role="pitcher" responsive />
  </div>

  {/* Central game area */}
  <div className="w-full lg:w-auto flex-1 lg:flex-none flex justify-center">
    <div className="w-36 h-36 sm:w-40 sm:h-40 md:w-48 md:h-48 lg:w-60 lg:h-60">
      {/* Central field graphics */}
    </div>
  </div>

  {/* Batter card */}
  <div className="w-full sm:w-1/2 lg:w-auto flex-shrink-0">
    <GameInfo role="batter" responsive />
  </div>
</div>
```

---

## 🟡 CONFIGURATION: Update tailwind.config.js

**File**: `frontend/tailwind.config.js`

### Add Custom Breakpoints:
```javascript
module.exports = {
  theme: {
    extend: {
      screens: {
        'xs': '375px',   // iPhone SE, small phones
        'sm': '640px',   // Standard phones (iPhone 12/13)
        'md': '768px',   // Tablets
        'lg': '1024px',  // Large tablets, small laptops
        'xl': '1280px',  // Laptops
        '2xl': '1536px', // Desktops
        '4k': '2560px',  // 4K monitors
      },
      fontSize: {
        'xs': '0.625rem',    // 10px
        'sm': '0.75rem',     // 12px
        'base': '1rem',      // 16px
        'lg': '1.125rem',    // 18px
        'xl': '1.25rem',     // 20px
      },
    }
  }
}
```

---

## 📱 Testing Checklist

After implementing fixes, test these scenarios:

### Mobile (375px - iPhone SE)
```
□ AuthScreen - form fits without horizontal scroll
□ LobbyScreen - buttons stack vertically
□ OnboardingScreen - team grid shows 1-2 columns
□ StadiumShowcaseScreen - panels stack vertically
□ Scoreboard - shows first 5 innings only
□ PlayerCard - readable without zoom
□ No horizontal scrolling anywhere
```

### Tablet (768px - iPad)
```
□ LobbyScreen - buttons in 2-3 column grid
□ OnboardingScreen - team grid shows 3-4 columns
□ StadiumShowcaseScreen - tighter layout, still readable
□ RosterSelectionScreen - field visible, panels stacked
□ All fonts >= 12px
```

### Desktop (1024px+)
```
□ StadiumShowcaseScreen - full 3-column layout
□ RosterSelectionScreen - full layout with field grid visible
□ Scoreboard - all 9 innings visible
□ No layout issues
□ Fonts at normal size
```

### 4K (2560px+)
```
□ No excessive whitespace
□ Fonts scale proportionally
□ Cards size appropriately
□ Layout remains balanced
```

---

## 🚀 Implementation Steps

1. **Start with Scoreboard** (3 hours)
   - Most isolated component
   - Great for testing responsive patterns
   - Used by StadiumShowcaseScreen

2. **Then PlayerCard** (2 hours)
   - Quick win
   - Isolate and test easily

3. **Then StadiumShowcaseScreen Main Layout** (6 hours)
   - Most complex
   - Depends on above components
   - Test extensively

4. **Continue with other screens** based on priority

---

## 📊 Metrics to Track

Before/After for each component:

```markdown
## Scoreboard.tsx
- Before: Breaks at < 1200px
- After: Works at 375px ✅
- Fonts readable: 5px → 6px min ✅

## PlayerCard.tsx
- Before: Card unreadable below 1400px
- After: Scales from 375px-4k ✅
- Stat fonts: 5px → 6px-11px ✅

## StadiumShowcaseScreen
- Before: Impossible to use below 1920px
- After: Responsive 375px-4k ✅
- Horizontal scroll: Yes → No ✅
```

---

**Document Version**: 1.0  
**Ready for**: Implementation  
**Estimated Total Time**: 30-35 hours across all screens  
**Priority Order**: Scoreboard → PlayerCard → StadiumShowcaseScreen → RosterSelectionScreen → Others
