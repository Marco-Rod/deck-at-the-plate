# PlayerCard Rarity Name Display Fix

## Problem
The rarity name in the top-left corner of player cards was truncated to only 3 letters:
- "DIA" instead of "DIAMOND"
- "GOL" instead of "GOLD"
- "SIL" instead of "SILVER"
- "BRO" instead of "BRONZE"
- "COM" instead of "COMMON"

This was caused by an explicit `.substring(0, 3)` call in the JSX.

## Solution
Removed the substring limitation and improved the flex layout to accommodate the full rarity names:

### Changes Made
**File:** `frontend/src/components/stadium/PlayerCard.tsx` (lines 155-161)

#### Before
```typescript
<div className="flex justify-between items-center border-b pb-1 sm:pb-1.5 md:pb-2 mb-2 md:mb-3" style={{ borderColor: tierConfig.accentColor }}>
  <span className={`font-mono ${headerSize} font-bold tracking-wider uppercase`} style={{ color: tierConfig.accentColor }}>
    {tierConfig.tierLabel.substring(0, 3)}  {/* ← TRUNCATED TO 3 CHARS */}
  </span>
  <span className={`font-mono text-sm sm:text-base md:text-lg font-bold`} style={{ color: tierConfig.accentColor }}>
    {player?.overall ?? '--'}
  </span>
</div>
```

#### After
```typescript
<div className="flex justify-between items-center border-b pb-1 sm:pb-1.5 md:pb-2 mb-2 md:mb-3 gap-1 w-full" style={{ borderColor: tierConfig.accentColor }}>
  <span className={`font-mono ${headerSize} font-bold tracking-wider uppercase truncate flex-1`} style={{ color: tierConfig.accentColor }}>
    {tierConfig.tierLabel}  {/* ← FULL NAME */}
  </span>
  <span className={`font-mono text-sm sm:text-base md:text-lg font-bold flex-shrink-0`} style={{ color: tierConfig.accentColor }}>
    {player?.overall ?? '--'}
  </span>
</div>
```

### Layout Improvements

| Property | Purpose |
|----------|---------|
| `gap-1` | Adds spacing between rarity name and overall rating |
| `w-full` | Container uses full available width |
| `flex-1` | Rarity label grows to fill available space |
| `truncate` | Fallback: if text too long, truncate with "..." instead of wrapping |
| `flex-shrink-0` | Overall rating maintains fixed size, never shrinks |

## Result

### Desktop (Large)
```
┌──────────────────┐
│ DIAMOND        99 │  ← Full names now visible
│ ────────────────  │
│       #7          │
│                   │
│     PLAYER NAME   │
│                   │
│ CON  POW  SPD    │
│ 75   82   68     │
│                   │
│ ⚾ YANKEES        │
└──────────────────┘
```

### Mobile (Small)
```
┌──────────┐
│ DIA    99│  ← Fits responsively
│ ─────────│
│    #7    │
│          │
│  PLAYER  │
│          │
│ C  P  S  │
│ 7  8  6  │
│          │
│⚾ NYY    │
└──────────┘
```

## Rarity Names Now Displayed

| Rarity | Previous | Now |
|--------|----------|-----|
| Diamond | DIA | DIAMOND |
| Gold | GOL | GOLD |
| Silver | SIL | SILVER |
| Bronze | BRO | BRONZE |
| Common | COM | COMMON |

## Responsive Behavior

1. **Desktop/Tablet:** Rarity name displays in full with no truncation
2. **Mobile:** Text may truncate with "..." if needed, but still shows more than 3 letters
3. **All sizes:** Overall rating stays right-aligned and maintains fixed width

## Testing

### Visual Test
1. Open stadium gameplay
2. Check pitcher card header - should show full rarity name
3. Check batter card header - should show full rarity name
4. Verify on different screen sizes (desktop, tablet, mobile)
5. Confirm names align properly and don't overlap with rating

### Expected Rarity Names
- ✓ DIAMOND (5 letters)
- ✓ GOLD (4 letters)
- ✓ SILVER (6 letters)
- ✓ BRONZE (6 letters)
- ✓ COMMON (6 letters)

## Files Modified
- `frontend/src/components/stadium/PlayerCard.tsx` (lines 155-161)

## Commit
`765c551` - "Fix: Show full rarity name in PlayerCard header"

## Related Issues
- Previous: Animation colors not updating when player changes (commit f29bd5a)
- Current: Rarity name truncated to 3 letters (FIXED)
- Next: Monitor for other display/truncation issues on small screens

## Summary
✅ Full rarity names now visible in card headers  
✅ Responsive layout adapts to screen size  
✅ Overall rating stays properly aligned  
✅ Truncate fallback for edge cases  
✅ Committed and ready for testing
