# PROPUESTA 1: Task Execution Guide
## Step-by-Step Instructions for Implementation

**Start Date:** 2026-08-25  
**Est. Duration:** 1.5-2 days  
**Status:** Ready to Start

---

## 🚀 QUICK START

### Prerequisites Check
```bash
# 1. Verify you're on development branch
git branch

# Expected: feature/propuesta-1-ui-hierarchy (create if missing)
git checkout -b feature/propuesta-1-ui-hierarchy

# 2. Verify frontend builds
cd frontend && npm run build 2>&1 | tail -20

# 3. Check if all files exist
ls -la src/components/stadium/{Scoreboard,GameInfo,PitchZoneGrid,TacticalHand,GameStatsPanel,PlayerCard,StadiumShowcaseScreen}.tsx
```

---

## 📋 TASK LIST - FOLLOW IN ORDER

### GROUP 1: SETUP (15 min)
**Goal:** Prepare workspace, verify current state

---

#### TASK 1.1: Create Development Branch
**Time:** 5 min  
**Complexity:** ⭐☆☆☆☆  
**Command:**
```bash
# Execute in project root
git checkout -b feature/propuesta-1-ui-hierarchy
git push -u origin feature/propuesta-1-ui-hierarchy
```
**Verification:** Branch appears in `git branch` output  
**Notes:** This branch will contain all Propuesta 1 changes

---

#### TASK 1.2: Document Current State
**Time:** 10 min  
**Complexity:** ⭐☆☆☆☆  
**Action:**
1. Open `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`
2. Scroll to line ~460 (header section)
3. Take note of CURRENT CSS classes:
   - Header: look for `flex justify-between items-center`
   - Scoreboard: look for font sizes (text-lg, text-md, etc.)
   - Card spacing: look for `gap-4` or similar
4. Document in a local file or notes

**Expected Output:**
```
CURRENT STATE SNAPSHOT:
- Header: flex justify-between items-center, pb-3
- Scoreboard: B/S/O = text-lg, Inning = text-md
- Card spacing: gap-4
- GameInfo: padding appears to be compact
```

**Notes:** This helps track what we're changing

---

### GROUP 2: HEADER & SCOREBOARD (45 min)
**Goal:** Improve visibility of top information

---

#### TASK 2.1: Update Header Layout (2-line format)
**Time:** 15 min  
**Complexity:** ⭐⭐☆☆☆  
**File:** `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  
**Lines:** ~460-475  

**Current Code (find this):**
```tsx
<header className="w-full flex justify-between items-center border-b-2 border-[#C5A059]/40 pb-3 mb-3 z-30">
  <div>
    <h2 className="font-sports text-3xl text-[#F7F5F0] uppercase tracking-wider leading-none">
      {userTeam ? `${userTeam.name} VS CPU` : 'CAMPO DE JUEGO'}
    </h2>
    <span className={`font-mono text-[10px] ${isConnected ? 'text-emerald-400' : 'text-red-400'}`}>
      {isConnected ? '● CONECTADO EN VIVO' : '○ DESCONECTADO'}
    </span>
  </div>
  <div className="flex items-center gap-3">
    <button type="button" onClick={onBack} className="bg-[#0A0D0F] border border-[#C5A059] px-4 py-2 font-mono text-xs text-[#C5A059] font-bold cursor-pointer hover:bg-[#1A3323]">
      ⚙️ LOBBY
    </button>
  </div>
</header>
```

**New Code (replace with this):**
```tsx
<header className="w-full border-b-2 border-[#C5A059]/40 pb-4 mb-3 z-30">
  <div className="flex justify-between items-start mb-2">
    <h2 className="font-sports text-4xl text-[#F7F5F0] uppercase tracking-wider leading-none">
      {userTeam ? `${userTeam.name} VS CPU` : 'CAMPO DE JUEGO'}
    </h2>
    <button type="button" onClick={onBack} className="bg-[#0A0D0F] border border-[#C5A059] px-4 py-2 font-mono text-xs text-[#C5A059] font-bold cursor-pointer hover:bg-[#1A3323]">
      ⚙️ LOBBY
    </button>
  </div>
  <span className={`font-mono text-[9px] ${isConnected ? 'text-emerald-400' : 'text-red-400'}`}>
    {isConnected ? '● CONECTADO EN VIVO' : '○ DESCONECTADO'}
  </span>
</header>
```

**Changes Summary:**
- Removed flex container from header itself
- Title: text-3xl → text-4xl
- Status: text-[10px] → text-[9px]
- Status moved outside div
- Padding: pb-3 → pb-4

**Visual Result:** Header has 2 lines, title is bigger, status is smaller and on its own line

**Verification Checklist:**
- [ ] No TypeScript errors
- [ ] Header renders on 2 lines
- [ ] Title is visibly larger
- [ ] Status text is smaller
- [ ] LOBBY button is top-right

---

#### TASK 2.2: Increase Scoreboard Font Sizes
**Time:** 15 min  
**Complexity:** ⭐⭐☆☆☆  
**File:** `frontend/src/components/stadium/Scoreboard.tsx`  

**Action Steps:**
1. Open file, find where B/S/O are rendered (search for "balls", "strikes")
2. Find each occurrence of font size and increase by ~33%:
   - `text-lg` (balls, strikes, outs) → `text-2xl`
   - `text-md` (inning) → `text-xl`
   - `text-sm` (hits) → `text-base`

**Code Pattern to Find:**
```tsx
// Look for patterns like:
<span className="text-lg">0</span>  // Balls
<span className="text-lg">2</span>  // Strikes
<span className="text-lg">1</span>  // Outs
```

**Code Pattern to Replace:**
```tsx
<span className="text-2xl">0</span>  // Balls (increased)
<span className="text-2xl">2</span>  // Strikes (increased)
<span className="text-2xl">1</span>  // Outs (increased)
```

**Find & Replace Shortcut:**
- Ctrl+H (Open Find & Replace)
- Find: `text-lg` (in Scoreboard section)
- Replace: `text-2xl`
- Repeat for `text-md` → `text-xl` and `text-sm` → `text-base`

**Verification Checklist:**
- [ ] B/S/O numbers are noticeably bigger
- [ ] Inning number is larger
- [ ] Hits are readable
- [ ] Component compiles without errors
- [ ] No overflow issues

---

#### TASK 2.3: Verify Scoreboard Rendering
**Time:** 10 min  
**Complexity:** ⭐☆☆☆☆  
**Action:**
1. Start dev server: `npm run dev` (if not already running)
2. Navigate to gameplay screen
3. Observe scoreboard at top
4. Compare with "before" snapshot from TASK 1.2
5. Verify B/S/O, Inning, Hits are all larger

**Expected Observation:**
- Numbers are ~33% larger than before
- Still fit within scoreboard without overflow
- Text is crisp and clear

**If Issues:**
- Check for text overflow (should not happen)
- Verify line-height hasn't been reduced
- Check that background is dark enough for contrast

---

### GROUP 3: CENTRAL FIELD SPACING (35 min)
**Goal:** Improve spacing in main game area

---

#### TASK 3.1: Increase Card Spacing (gap-4 to gap-6)
**Time:** 10 min  
**Complexity:** ⭐⭐☆☆☆  
**File:** `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  
**Lines:** ~517-530 (look for cards div)

**Current Code (find this):**
```tsx
<div className="w-full flex justify-center items-start gap-4">
  {/* PlayerCard pitcher */}
  {/* PitchZoneGrid */}
  {/* PlayerCard batter */}
</div>
```

**New Code (replace with this):**
```tsx
<div className="w-full flex justify-center items-start gap-6">
  {/* PlayerCard pitcher */}
  {/* PitchZoneGrid */}
  {/* PlayerCard batter */}
</div>
```

**Changes:**
- `gap-4` → `gap-6` (16px → 24px spacing)

**Verification:**
- [ ] Cards have visible space between them
- [ ] Cards don't overlap
- [ ] Grid is centered
- [ ] Layout looks balanced

---

#### TASK 3.2: Improve GameInfo (B/S/O, Bases, Inning)
**Time:** 15 min  
**Complexity:** ⭐⭐⭐☆☆  
**File:** `frontend/src/components/stadium/GameInfo.tsx`  

**Action Steps:**
1. Open `GameInfo.tsx`
2. Find the main container (outer div)
3. Increase internal padding: 10px → 15px
4. Find all text elements that show B/S/O, Bases, Inning
5. Increase their font sizes:
   - Labels (B, S, O, etc): `text-sm` → `text-base`
   - Values (0, 2, 1, etc): `text-lg` → `text-2xl`

**Code Pattern:**
```tsx
// BEFORE
<div className="p-2 ..." >
  <span className="text-sm">Balls</span>
  <span className="text-lg">0</span>
</div>

// AFTER
<div className="p-4 ..." >
  <span className="text-base">Balls</span>
  <span className="text-2xl">0</span>
</div>
```

**Verification:**
- [ ] More breathing room inside component
- [ ] Text is bigger and more readable
- [ ] Component doesn't overflow container
- [ ] Still aligns well with cards above/below

---

#### TASK 3.3: Enhance Dynamic Message Styling
**Time:** 10 min  
**Complexity:** ⭐⭐☆☆☆  
**File:** `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  
**Lines:** ~533-538 (look for "El lanzador ya pichó")

**Current Code (find this):**
```tsx
{hasPitched && role === 'BATTER' && (
  <div className="mt-2 bg-[#C5A059] text-[#0A0D0F] px-4 py-1 font-mono text-xs font-bold z-20 animate-bounce">
    ¡El lanzador ya pichó! Selecciona tu swing.
  </div>
)}
```

**New Code (replace with this):**
```tsx
{hasPitched && role === 'BATTER' && (
  <div className="mt-2 bg-[#C5A059]/90 text-[#0A0D0F] px-6 py-2 font-mono text-sm font-bold z-20 animate-bounce rounded-sm shadow-lg">
    ¡El lanzador ya pichó! Selecciona tu swing.
  </div>
)}
```

**Changes:**
- Padding: `px-4 py-1` → `px-6 py-2` (more space around text)
- Font: `text-xs` → `text-sm` (bigger text)
- Opacity: `bg-[#C5A059]` → `bg-[#C5A059]/90` (slightly transparent)
- Added: `rounded-sm shadow-lg` (polish)

**Verification:**
- [ ] Message is more visible
- [ ] Text is easier to read
- [ ] Padding looks balanced
- [ ] No visual issues

---

### GROUP 4: LATERAL PANELS (70 min)
**Goal:** Redesign lineup and strikeouts panels

---

#### TASK 4.1: Verify GameStatsPanel Component
**Time:** 5 min  
**Complexity:** ⭐☆☆☆☆  
**Action:**
Check if file exists:
```bash
ls -la frontend/src/components/stadium/GameStatsPanel.tsx
```

**If EXISTS:**
- Go to TASK 4.3 (skip 4.2)
- Document current structure (props, render logic)

**If NOT EXISTS:**
- Go to TASK 4.2 (create component)
- Then proceed to 4.3

---

#### TASK 4.2: Create GameStatsPanel.tsx Component
**Time:** 30 min  
**Complexity:** ⭐⭐⭐⭐☆  
**File:** Create `frontend/src/components/stadium/GameStatsPanel.tsx`

**Action:** Copy this complete component:

```tsx
import React from 'react';

interface GameStatsPanelProps {
  lineup: Array<{ id?: string; name: string; number: string; photo?: string; overall?: number; position?: string }>;
  stats: Record<string, any>;
  isPitcher: boolean;
  pitcherStrikeouts?: number;
  pitcherName?: string;
  animateStrikeout?: boolean;
}

export const GameStatsPanel: React.FC<GameStatsPanelProps> = ({
  lineup,
  stats,
  isPitcher,
  pitcherStrikeouts = 0,
  pitcherName = 'Pitcher',
  animateStrikeout = false,
}) => {
  if (isPitcher) {
    // RIGHT PANEL: STRIKEOUTS
    return (
      <div className="bg-[#0A0D0F]/80 border border-[#C5A059]/40 rounded-sm p-5 text-center h-full flex flex-col justify-center">
        {/* Pitcher Name */}
        <div className="text-[#F7F5F0] font-sports text-2xl uppercase mb-4 truncate">
          {pitcherName}
        </div>

        {/* Strikeout Counter */}
        <div className="flex flex-col items-center my-6">
          <div className={`font-sports text-6xl text-[#FFD700] transition-all ${animateStrikeout ? 'scale-110' : 'scale-100'}`}>
            {pitcherStrikeouts}
          </div>
          <div className="text-[#C5A059] text-xs font-mono font-bold mt-2 tracking-widest">
            STRIKEOUTS
          </div>
        </div>

        {/* Inning Stats (Optional) */}
        <div className="border-t border-[#C5A059]/20 pt-3 mt-4 text-[8px] text-[#E6DFD3] font-mono space-y-1">
          <div className="flex justify-between">
            <span>PITCHES:</span>
            <span>--</span>
          </div>
          <div className="flex justify-between">
            <span>WHIFFS:</span>
            <span>--</span>
          </div>
          <div className="flex justify-between">
            <span>BALLS:</span>
            <span>--</span>
          </div>
        </div>
      </div>
    );
  }

  // LEFT PANEL: LINEUP
  return (
    <div className="bg-[#0A0D0F]/80 border border-[#C5A059]/40 rounded-sm p-3 h-full flex flex-col">
      {/* Header */}
      <div className="mb-3">
        <h3 className="text-sm text-[#F7F5F0] font-sports font-bold uppercase tracking-wider">
          📊 YOUR LINEUP
        </h3>
        <p className="text-[8px] text-[#C5A059] font-mono mt-1">
          vs PITCHER: --
        </p>
      </div>

      {/* Lineup Items Container (Scrollable) */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {lineup && lineup.length > 0 ? (
          lineup.map((player, idx) => (
            <div key={player.id || idx} className="text-[8px]">
              <div className="flex justify-between items-center text-[#F7F5F0] font-mono mb-0.5">
                <span className="font-bold">#{player.number} {player.name}</span>
                <span className="text-[#C5A059]">{player.overall || 0}</span>
              </div>
              <div className="text-[#E6DFD3] ml-2">
                <span>{player.position || '--'}</span>
                <span className="ml-2">| --</span>
              </div>
              {idx < (lineup.length - 1) && (
                <div className="border-t border-[#C5A059]/20 mt-2" />
              )}
            </div>
          ))
        ) : (
          <div className="text-[#C5A059]/60 text-[8px] text-center py-4">
            No lineup data
          </div>
        )}
      </div>
    </div>
  );
};
```

**Verification:**
- [ ] File is created in correct path
- [ ] TypeScript compiles without errors
- [ ] Component exports properly

---

#### TASK 4.3: Update Lineup Panel Styling (LEFT)
**Time:** 15 min  
**Complexity:** ⭐⭐⭐☆☆  
**File:** `frontend/src/components/stadium/GameStatsPanel.tsx` (just created)

**Review the component you created in 4.2:**
- Left panel (isPitcher=false) should show:
  - Header "📊 YOUR LINEUP" (text-sm)
  - Subtitle "vs PITCHER: --" (text-[8px], in #C5A059)
  - Scrollable list of players
  - Each player: #Number Name → Position | Stats
  - Separators between players

**If component looks correct:**
- [ ] Verify all styling is applied
- [ ] Check padding/margin balance
- [ ] Confirm scrolling works
- [ ] Text sizes are readable

**If adjustments needed:**
- Increase header: text-xs → text-sm
- Increase scrollable area: adjust max-h if needed
- Improve separator visibility: border-t with proper color
- Add more spacing between items if compressed

---

#### TASK 4.4: Update Strikeouts Panel Styling (RIGHT)
**Time:** 15 min  
**Complexity:** ⭐⭐⭐☆☆  
**File:** `frontend/src/components/stadium/GameStatsPanel.tsx` (just created)

**Review the component you created in 4.2:**
- Right panel (isPitcher=true) should show:
  - Pitcher name: text-2xl, uppercase
  - Large SO counter: text-6xl (very big)
  - "STRIKEOUTS" label below
  - Optional: Inning stats (Pitches, Whiffs, Balls)

**Verification:**
- [ ] SO number is very prominent (text-6xl)
- [ ] Pitcher name is readable
- [ ] Label "STRIKEOUTS" is visible
- [ ] Padding is generous (p-5)
- [ ] Animation triggers on animateStrikeout prop

**If adjustments needed:**
- Increase counter size if text-6xl feels small
- Add more vertical padding (p-5 → p-6)
- Improve label contrast if hard to read
- Test animation smoothness

---

#### TASK 4.5: Connect GameStatsPanel to StadiumShowcaseScreen
**Time:** 10 min  
**Complexity:** ⭐⭐☆☆☆  
**File:** `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  

**Action Steps:**
1. Near top of file, add import:
```tsx
import { GameStatsPanel } from './GameStatsPanel';
```

2. Scroll to line ~485 (LEFT panel section)
3. Verify it renders GameStatsPanel with correct props:
```tsx
<GameStatsPanel
  lineup={getBattingLineup()}
  stats={gameStats?.batters || {}}
  isPitcher={false}
/>
```

4. Scroll to line ~498 (RIGHT panel section)
5. Verify it renders GameStatsPanel with correct props:
```tsx
<GameStatsPanel
  lineup={[]}
  stats={{}}
  isPitcher={true}
  pitcherStrikeouts={getPitcherStrikeouts()}
  pitcherName={getActivePitcherName()}
  animateStrikeout={strikeoutAnimationTrigger}
/>
```

**Verification:**
- [ ] Import statement exists and has correct path
- [ ] Both panels render without errors
- [ ] LEFT panel shows lineup
- [ ] RIGHT panel shows SO counter
- [ ] No TypeScript errors

---

### GROUP 5: POLISH & TESTING (30 min)
**Goal:** Final tweaks and comprehensive testing

---

#### TASK 5.1: Review PitchZoneGrid Header (Optional)
**Time:** 10 min  
**Complexity:** ⭐⭐☆☆☆  
**File:** `frontend/src/components/stadium/PitchZoneGrid.tsx`  

**Action:**
1. Open file
2. Look for the main grid container
3. Consider adding a header "STRIKE ZONE" above grid
4. If added, ensure contrast is good and label is clear

**Optional Enhancement:**
```tsx
// Add above grid:
<div className="text-center mb-2">
  <h4 className="text-xs text-[#C5A059] font-mono font-bold tracking-wider">
    STRIKE ZONE
  </h4>
</div>
```

**Verification:**
- [ ] If added, label is visible and clear
- [ ] Grid is still properly centered
- [ ] No layout issues

---

#### TASK 5.2: Review TacticalHand Layout
**Time:** 10 min  
**Complexity:** ⭐⭐☆☆☆  
**File:** `frontend/src/components/stadium/TacticalHand.tsx`  

**Action:**
1. Open file
2. Look for card container spacing (search for `gap-`)
3. Verify gap is adequate: `gap-3` or larger preferred
4. Check if cards are evenly distributed
5. Consider if layout is 4 cards in 2x2 or horizontal line

**Current:** Likely `gap-2` or `gap-3`  
**Target:** `gap-3` (12px minimum)

**If adjustment needed:**
```tsx
// Find:
className="... flex gap-2 ..."

// Change to:
className="... flex gap-3 ..."
```

**Verification:**
- [ ] Cards have visible spacing
- [ ] No overlap
- [ ] Layout looks balanced

---

#### TASK 5.3: Visual Comprehensive Testing
**Time:** 15 min  
**Complexity:** ⭐☆☆☆☆  
**Environment:** Browser at localhost:3000

**Setup:**
1. Start dev server if not running: `npm run dev`
2. Open DevTools: F12
3. Open Performance tab (for FPS monitoring)
4. Navigate to gameplay screen

**Checklist - Visual Elements:**
- [ ] Header: 2 lines, title is text-4xl (looks big)
- [ ] Header: State/connection text is smaller, below title
- [ ] Scoreboard: B/S/O numbers are text-2xl (noticeably larger)
- [ ] Scoreboard: Inning number is text-xl
- [ ] GameInfo: Larger, more readable, good padding
- [ ] Central field: Cards have gap-6 (good spacing)
- [ ] Message: "El lanzador ya pichó!" is bigger, more visible
- [ ] LEFT panel: Header is text-sm, subtitle shows pitcher name
- [ ] LEFT panel: Lineup items are scrollable, separated with lines
- [ ] LEFT panel: Text is readable despite small font
- [ ] RIGHT panel: SO counter is HUGE (text-6xl)
- [ ] RIGHT panel: "STRIKEOUTS" label is visible
- [ ] TacticalHand: Cards have good spacing (gap-3)

**Checklist - Responsive:**
- [ ] Layout looks good on 1920x1080
- [ ] Try 1366x768 - still readable
- [ ] No horizontal scrollbars appear
- [ ] Cards don't overflow

**Checklist - Performance:**
- [ ] Monitor FPS: should be 58-60
- [ ] No frame drops during interaction
- [ ] No console errors
- [ ] Smooth animations (hovers, transitions)

**If Issues Found:**
- Document them
- Note which component/section has issue
- Plan fix (go to specific TASK)

---

#### TASK 5.4: Final Review & Commit
**Time:** 5 min  
**Complexity:** ⭐☆☆☆☆  

**Action Steps:**
1. Go back to `Scoreboard.tsx` if you made changes
2. Verify no console errors: Open DevTools → Console tab
3. Check for TypeScript errors: Look for red squiggles
4. Stage changes:
```bash
git add frontend/src/components/stadium/
git add .kiro/specs/
```

5. Commit:
```bash
git commit -m "feat: propuesta-1-ui-hierarchy - improved visual clarity and spacing"
```

6. Push:
```bash
git push origin feature/propuesta-1-ui-hierarchy
```

**Verification:**
- [ ] No errors in console
- [ ] No TypeScript errors
- [ ] Git commit successful
- [ ] Branch is pushed

---

## 🎯 Summary of Changes

### Files Modified:
1. **StadiumShowcaseScreen.tsx**
   - Header: 2-line layout, text-4xl title
   - Card spacing: gap-4 → gap-6
   - Message styling: px-4 py-1 → px-6 py-2, text-xs → text-sm
   - GameStatsPanel imports/usage

2. **Scoreboard.tsx**
   - B/S/O: text-lg → text-2xl
   - Inning: text-md → text-xl
   - Hits: text-sm → text-base

3. **GameInfo.tsx**
   - Padding: ~10px → 15px
   - Labels: text-sm → text-base
   - Values: text-lg → text-2xl

4. **GameStatsPanel.tsx** (NEW)
   - Left panel: Lineup display with scrolling
   - Right panel: SO counter with large numbers

5. **PitchZoneGrid.tsx** (Optional)
   - Add "STRIKE ZONE" header if desired

6. **TacticalHand.tsx** (Minor)
   - Verify gap-3 or increase spacing

### Files Created:
- `.kiro/specs/PROPUESTA_1_SPEC.md` (this spec)
- `.kiro/specs/PROPUESTA_1_TASKS.md` (this guide)
- `frontend/src/components/stadium/GameStatsPanel.tsx` (if didn't exist)

---

## ⏱️ Time Breakdown

| Task | Time | Status |
|------|------|--------|
| Setup | 15 min | Pending |
| Header & Scoreboard | 45 min | Pending |
| Central Spacing | 35 min | Pending |
| Lateral Panels | 70 min | Pending |
| Polish & Testing | 30 min | Pending |
| **TOTAL** | **195 min (3.25h)** | **Estimated** |

**Typical Day:** 1-2 days depending on complexity of existing code structure

---

## 🚨 Troubleshooting

### Issue: TypeScript errors in GameStatsPanel
**Solution:** Check that all props are properly typed in interface at top of file

### Issue: Cards overlapping after gap-6 change
**Solution:** Check container width, may need to adjust max-width or container layout

### Issue: Left panel scrollbar not appearing
**Solution:** Verify `overflow-y-auto` is set and height constraints are correct

### Issue: SO counter looks too big
**Solution:** Adjust text-6xl down to text-5xl if needed, or add more padding to balance

### Issue: Header button overlapping title on mobile
**Solution:** Use responsive classes: `flex-col md:flex-row` to stack on mobile

---

## ✅ DEFINITION OF DONE

Propuesta 1 is complete when:
1. ✅ All TASKS 1.1 through 5.4 are completed
2. ✅ No TypeScript or console errors
3. ✅ Visual checklist (TASK 5.3) fully passed
4. ✅ FPS maintained at 58-60
5. ✅ Code committed to feature branch
6. ✅ User visually confirms improvement

---

## 📞 Support

If stuck on any task:
1. Review the task description again
2. Check the code examples
3. Compare with BEFORE state from TASK 1.2
4. Check component imports are correct
5. Verify file paths are accurate

