# PlayerCard Animation Color Bug Fix

## Problem Description
When a new batter/pitcher entered the game, the player card border updated correctly to the new rarity color, but the glow/shadow effect around the card remained the color from the previous player. This visual inconsistency affected the entire card appearance.

### Example
1. DIAMOND pitcher enters (purple glow) ✓ Correct
2. Batter swings, play ends
3. GOLD batter enters:
   - Border: Updates to gold ✓ Correct
   - Glow/Shadow: Still shows purple ✗ BUG - Should be gold

## Root Cause
The `PlayerCard` component uses Framer Motion for animations with `boxShadow` interpolation:

```typescript
// Lines 116-135 in PlayerCard.tsx
animate: {
  boxShadow: [
    `0 0 20px ${tierConfig.shadowColor}, inset 0 0 10px rgba(255, 255, 255, 0.05)`,
    `0 0 40px ${tierConfig.shadowColor}, inset 0 0 15px rgba(255, 255, 255, 0.1)`,
    `0 0 20px ${tierConfig.shadowColor}, inset 0 0 10px rgba(255, 255, 255, 0.05)`,
  ],
  transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' }
}
```

**Issue:** Framer Motion caches the animation keyframes the first time they're created. When `tierConfig.shadowColor` changes (because the player changed), the animation doesn't re-evaluate the string interpolation - it continues using the cached values from the previous render.

## Solution
Added a `key` prop to the `motion.div` that changes whenever the player changes:

```typescript
// Line 140 in PlayerCard.tsx
<motion.div
  key={player?.id}  // ⭐ NEW: Force re-mount when player changes
  // ... rest of props
>
```

**How it works:**
1. When `player?.id` changes (new batter/pitcher enters)
2. React unmounts the old `motion.div` and mounts a new one
3. Framer Motion creates fresh animation keyframes
4. The new keyframes use the current `tierConfig.shadowColor`
5. Animation plays with the correct rarity color

## Implementation Details

### File Modified
`frontend/src/components/stadium/PlayerCard.tsx` (line 140)

### Change
```diff
  return (
    <motion.div
+     key={player?.id} // ⭐ NEW: Force re-mount when player changes to reset animations
      className={...}
      style={{...}}
      animate={animationConfig.animate}
      transition={animationConfig.transition}
      whileHover={animationConfig.whileHover}
      whileTap={animationConfig.whileTap}
    >
```

### Data Flow
1. `StadiumShowcaseScreen` receives `active_batter`/`active_pitcher` from WebSocket
2. Updates `batterCard`/`pitcherCard` state with new `PlayerData` (including `id` and `rarity`)
3. Props passed to `CentralField` component
4. `CentralField` renders `PlayerCard` with `player={batterCard}` or `player={pitcherCard}`
5. PlayerCard component detects `player?.id` changed
6. React re-mounts the `motion.div` with new key
7. Framer Motion creates fresh animation with new `tierConfig.shadowColor`
8. Glow effect now matches border color

## Affected Components
- `PlayerCard.tsx` - Receives key prop
- `CentralField.tsx` - Passes playerCard objects (no changes needed)
- `StadiumShowcaseScreen.tsx` - Provides playerCard data (no changes needed)

## Testing Instructions

### Visual Test
1. Start a new game in stadium
2. First at-bat begins with DIAMOND pitcher (purple glow)
3. Observe: Border is purple, glow is purple ✓
4. First batter hits, play resolves
5. Second batter enters (different rarity, e.g., GOLD)
6. **Expected:** Border updates to gold, glow updates to gold ✓
7. **Before fix:** Border gold, glow still purple ✗
8. **After fix:** Both update immediately ✓

### Repeat Test
- Test multiple player changes
- Verify pitcher changes also work correctly
- Try different rarity combinations (DIAMOND→GOLD, SILVER→BRONZE, etc.)

### Browser DevTools
1. Open Components tab
2. Filter for PlayerCard
3. Inspect the motion.div element
4. Watch the `key` attribute change when player changes
5. Verify `style.boxShadow` updates with new color

## Color Reference
```
DIAMOND:  rgba(153, 102, 255, 0.8)   [Purple]
GOLD:     rgba(255, 215, 0, 0.7)     [Gold]
SILVER:   rgba(192, 192, 192, 0.6)   [Silver]
BRONZE:   rgba(205, 127, 50, 0.6)    [Bronze]
COMMON:   rgba(128, 128, 128, 0.5)   [Gray]
```

## Why This Solution Works
- **Simple:** Only adds a single `key` prop
- **Performant:** Component re-mount is fast (no complex logic)
- **Reliable:** React's reconciliation algorithm guarantees component unmount/mount
- **Clean:** No need to manually reset animation state or use refs
- **Scalable:** Works for any PlayerCard instance (pitcher, batter, or future cards)

## Related Issues
- Previous: Rarity values missing from WebSocket payload (fixed in commit 1a5dcb4)
- Current: Animation colors not updating on player change (fixed in commit f29bd5a)
- Next: Monitor for other animation state issues when props change rapidly

## Summary
✅ Root cause identified: Framer Motion animation caching  
✅ Solution implemented: React key-based component re-mount  
✅ Both pitcher and batter cards affected and fixed  
✅ Committed: `f29bd5a`  
✅ Ready for testing in stadium gameplay
