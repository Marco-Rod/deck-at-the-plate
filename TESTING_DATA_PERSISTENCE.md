# Data Persistence Testing Guide

## Issue Fixed
Missing data persistence in frontend UI after first game event. Properties like `pitchCount`, `activePitcherName`, stats disappeared after second event despite WebSocket sending correct data.

## Root Cause
- `GameStateWS` type was missing `inning_completed` property definition
- `parseStateData()` was not returning `inning_completed` from backend payload
- `useEffect` dependency at line 527 was trying to access `inningCompleted?.ts` which was always `undefined`

## Fix Applied

### 1. Added Property to Type (frontend/src/types/stadium.ts)
```typescript
export interface GameStateWS {
  // ... other properties
  inning_completed?: boolean; // Flag from backend when inning completes
}
```

### 2. Updated Parser (frontend/src/hooks/useStadiumSocket.ts)
```typescript
export function parseStateData(payload: { 
  // ... other properties
  inning_completed?: any 
}): GameStateWS {
  return {
    // ... other properties
    inning_completed: payload.inning_completed, // ✅ Now extracts from payload
  };
}
```

### 3. Fixed Dependency (frontend/src/components/stadium/StadiumShowcaseScreen.tsx)
```typescript
// Ref to track boolean changes from backend
const prevInningCompletedRef = useRef<boolean | undefined>(undefined);

// State to hold timestamp version
const [inningCompletedTimestamp, setInningCompletedTimestamp] = useState<{ ts: number } | undefined>(undefined);

// Convert boolean→true transition to timestamp (prevents infinite loops)
useEffect(() => {
  const currentInningCompleted = gameState?.inning_completed === true;
  const prevInningCompleted = prevInningCompletedRef.current;
  
  if (currentInningCompleted && !prevInningCompleted) {
    setInningCompletedTimestamp({ ts: Date.now() });
  } else if (!currentInningCompleted && prevInningCompleted) {
    setInningCompletedTimestamp(undefined);
  }
  
  prevInningCompletedRef.current = currentInningCompleted;
}, [gameState?.inning_completed]);

// useEffect dependency now uses timestamp (no more undefined issues)
useEffect(() => {
  // ... inning transition logic
}, [inningCompletedTimestamp.ts, gameState, lastResult]);
```

## Testing Steps

### Prerequisites
- Docker containers running (frontend on port 5173, backend on port 8000)
- Browser dev tools open (F12 or Ctrl+Shift+I)
- Console tab ready to monitor logs

### Test Procedure

**Step 1: Start a New Game**
1. Navigate to stadium gameplay screen
2. Open browser console (F12 → Console tab)
3. Clear any previous logs
4. Watch console for `[PARSE_STATE_DATA]` and `[GAMESTATE UPDATED]` logs

**Step 2: Monitor First Event**
1. Execute first action (e.g., throw pitch → batter swings)
2. Look for log: `🔵 [FRONTEND] PLAY_RESOLVED received`
3. Verify in console output:
   - ✅ `pitchCount: 1` (or appropriate count)
   - ✅ `activePitcherName: 'Name'` (not undefined)
   - ✅ `fatigueLevel: 0` or number (not undefined)
   - ✅ Stats visible (strikeouts, hits, etc.)

**Step 3: Monitor Second Event**
1. Execute second action (e.g., next pitch)
2. Look for log: `🔵 [FRONTEND] PLAY_RESOLVED received`
3. **CRITICAL CHECK** - Verify data PERSISTS:
   - ✅ `pitchCount: 2` (incremented, not undefined)
   - ✅ `activePitcherName: 'Name'` (still present, not undefined)
   - ✅ `fatigueLevel: XX` (still present, not undefined)
   - ✅ Stats still visible (should show accumulated totals)

**Step 4: Monitor Inning Completion**
1. Continue playing until 3 outs (end of half-inning)
2. Look for logs:
   - `⭐ [INNING COMPLETED] Nueva entrada finalizada, generando timestamp`
   - Should see modal transition (if not game-over)
3. Verify `inningCompletedTimestamp` is now defined (logged in step 2)

**Step 5: Monitor Third+ Events**
1. Continue to third and subsequent events
2. Repeat checks from Step 3
3. Verify data continues to persist through all events

### Expected Console Logs

**On INIT_GAME_STATE:**
```
⭐ [PARSE_STATE_DATA] pitcher_strikeouts: {...}
⭐ [PARSE_STATE_DATA] batter_stats keys: [...]
⭐ [PARSE_STATE_DATA] hits: { home_hits: 0, away_hits: 0 }
⭐ [PARSE_STATE_DATA] inning_completed: false
```

**On PLAY_RESOLVED (First Event):**
```
🔵 [FRONTEND] PLAY_RESOLVED received:
   event: STRIKE_LOOKING
   score_home: 0
   score_away: 0
⭐ [PARSE_STATE_DATA] pitcher_strikeouts: {pitcher_id: 1}
⭐ [PARSE_STATE_DATA] inning_completed: false
📍 [GAMESTATE UPDATED] State actualizado desde PLAY_RESOLVED
```

**On PLAY_RESOLVED (Second Event - CRITICAL):**
```
🔵 [FRONTEND] PLAY_RESOLVED received:
   event: HOME_RUN
   score_home: 1
   score_away: 0
⭐ [PARSE_STATE_DATA] pitcher_strikeouts: {pitcher_id: 2}  ← Incremented
⭐ [PARSE_STATE_DATA] inning_completed: false
📍 [GAMESTATE UPDATED] State actualizado desde PLAY_RESOLVED
```

**On Inning Completion:**
```
⭐ [INNING COMPLETED] Nueva entrada finalizada, generando timestamp
🎮 [INNING_TRANSITION] Modal de transición mostrado
```

### Success Criteria

✅ **PASS**: 
- First event shows pitcher data (pitchCount, activePitcherName, stats)
- Second event also shows pitcher data (values persisted, not undefined)
- Data continues through all subsequent events
- `inningCompletedTimestamp` generates only once per inning end
- No console errors about undefined properties

❌ **FAIL**:
- Second+ events show undefined values
- `activePitcherName` disappears after first event
- Stats reset or become empty
- Console errors like "Cannot read property 'ts' of undefined"
- `inningCompletedTimestamp` keeps regenerating

### Manual Browser Verification

In browser console, check gameState directly:
```javascript
// After first event, run in console:
console.log('Pitcher Name:', gameState?.active_pitcher?.name);
console.log('Pitch Count:', gameState?.active_pitcher?.pitch_count);
console.log('Fatigue:', gameState?.active_pitcher?.fatigue_level);

// After second event, run same command
// Expected: Same data persists (not undefined)
```

## Debugging Tips

### If data is still missing after second event:

1. **Check backend payload:**
   - Backend logs should show `[PLAY_RESOLVED PAYLOAD]` with all fields
   - Verify `inning_completed: boolean` is present
   - Verify `active_pitcher` object has all fields

2. **Check frontend parsing:**
   - Look for `⭐ [PARSE_STATE_DATA] active_pitcher rarity:` in console
   - Should show pitcher data, not undefined

3. **Check state update:**
   - Look for `📍 [GAMESTATE UPDATED]` after each PLAY_RESOLVED
   - Verify timestamp shows recent time

4. **Check effect dependency:**
   - Verify `⭐ [INNING COMPLETED]` log appears when inning ends
   - Should see timestamp being generated

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `undefined` after 2nd event | Old data being overwritten | Check parseStateData returns all fields |
| `pitchCount` missing | active_pitcher not included | Verify backend sends active_pitcher in PLAY_RESOLVED |
| `inningCompletedTimestamp` undefined | useEffect not converting boolean | Check prevInningCompletedRef logic |
| Infinite loops | timestamp regenerating every render | Verify useEffect only runs on inning_completed change |

## Database/Backend Verification

If frontend still shows issues after fixes:

1. Check database has game state: `SELECT * FROM games WHERE id='game_xxx'`
2. Check state_data has pitcher info: `SELECT state_data->>'active_pitcher' FROM games WHERE id='game_xxx'`
3. Check WebSocket message in browser network tab: Filter for `ws` protocol, look for message content

## Files Modified

- ✅ `frontend/src/types/stadium.ts` - Added inning_completed property
- ✅ `frontend/src/hooks/useStadiumSocket.ts` - Extract inning_completed from payload
- ✅ `frontend/src/components/stadium/StadiumShowcaseScreen.tsx` - Convert boolean to timestamp

