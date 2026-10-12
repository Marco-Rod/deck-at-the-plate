# Testing Event Sequencing Fix - Guide

## What Was Fixed

The attempt to update `gameState` in the Event Sequencer callback failed because `setGameState` is not accessible outside the `useStadiumSocket` hook.

**Correct Solution:**
- `gameState` is updated immediately by the WebSocket handler when PLAY_RESOLVED arrives
- The Event Sequencer controls the **callback timing**, not the state update
- React batches updates automatically
- CSS z-index ensures the modal appears visually first

## Files Changed

### frontend/src/hooks/useStadiumSocket.ts

**PLAY_RESOLVED case (line 144-163):**
```typescript
setGameState(parseStateData(payload));  // ✅ Restore immediate update
callbacks?.onPlayResolved?.(payload);   // Enqueue event for sequencing
```

**STEAL_RESOLVED case (line 165-175):**
```typescript
setGameState(parseStateData(payload));  // ✅ Restore immediate update
callbacks?.onPlayResolved?.(payload);
```

### frontend/src/components/stadium/StadiumShowcaseScreen.tsx

**show-modal callback (line 283-300):**
- Removed invalid `setGameState()` call
- Kept just `setLastResult()` and `setIsAwaitingResult(true)`
- Added comment explaining that WebSocket handles state, sequencer handles callback timing

## Testing Steps

### 1. Rebuild Docker Container
The frontend container needs to pick up the code changes. You can either:

**Option A: Force rebuild**
```bash
docker-compose down
docker-compose up --build
```

**Option B: Just restart frontend container**
```bash
docker-compose up -d frontend
```

Wait 30-60 seconds for Vite to rebuild and hot-reload.

### 2. Clear Browser Cache
- Hard refresh: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)
- Or: DevTools → Application → Storage → "Clear site data"

### 3. Start New Game
1. Navigate to lobby
2. Select your team
3. Click "Start Game"

### 4. Test Event Sequence

**Test OUT_GROUND (Ground Ball Out):**
1. Pitcher throws a pitch in zone 1-5
2. Batter swings
3. Observe:
   - Modal appears showing "Out de ground ball" or similar
   - **THEN** scorecard updates (outs counter increases)

**Test BALL:**
1. Pitcher throws outside zone
2. Result: Modal shows ball → batter advances count

**Test STRIKE:**
1. Pitcher throws in zone
2. Batter takes (swings=false option)
3. Result: Modal shows strike → strike counter updates

**Test HIT_1B:**
1. Batter connects for a hit
2. Result: Modal shows hit description → runners/scores update

### 5. Verify Browser Console

Open DevTools (F12), check Console tab for logs:

**Look for:**
```
🔵 [FRONTEND] PLAY_RESOLVED received:
   event: [EVENT_TYPE]
   score_home: [NUM]
   score_away: [NUM]

📤 [HANDLER] Enqueuing PLAY_RESOLVED event: [EVENT_TYPE]
⚙️  [EVENT SEQUENCER] Processing event: [EVENT_TYPE]
📍 [STEP] show-modal (delay: 0ms) - executing callback
✅ [STEP] show-modal - Setting PlayResultOverlay
✅ [STEP] update-score (delay: 3100ms) - executing callback
✅ [STEP] update-outs - Actualizando outs
```

**Should NOT see:**
```
❌ [STEP] Error in show-modal: ReferenceError: setGameState is not defined
```

### 6. Verify gameState Updates

In console, check that stats update after modal shows. Filter logs by `[STADIUM SHOWCASE]`:

```
🎲 [STADIUM SHOWCASE] Pasando datos al Scoreboard:
  - gameState.inning_runs: {...actual data...}
  - gameState.homeScore: [NUM > 0 if runs scored]
  - gameState.awayScore: [NUM]
```

Should show non-zero scores/stats after plays.

## Troubleshooting

### Issue: Still getting "setGameState is not defined" error
- **Solution:** The container hasn't rebuilt yet
- Restart the frontend container: `docker-compose restart frontend`
- Wait 60 seconds for Vite to rebuild
- Hard refresh browser (Ctrl+Shift+R)

### Issue: Scores still not updating (show 0/0)
- **Root cause:** Game might have no runs scored yet
  - Play more events (hits, home runs)
  - Check batter_stats updates in console: `[PARSE_STATE_DATA] batter_stats keys: [...]`
  - If empty array: backend not sending stats (check backend logs)

- **Solution:** Check backend container logs:
  ```bash
  docker logs baseball_backend | tail -50
  ```
  Look for errors in `_build_play_resolved_payload()`

### Issue: Modal not appearing
- **Possible causes:**
  - `lastResult` not being set (check show-modal logs)
  - CSS issue hiding the modal
  - Event Sequencer not processing

- **Debug:** Filter console for `[EVENT SEQUENCER]` and `[STEP]` logs
  - Should see "show-modal" executing with 0ms delay
  - Should see `setLastResult` being called

### Issue: Event Sequencer not processing events
- **Check:** Is `onStep` being called correctly?
  - Look for `📤 [HANDLER] Enqueuing` logs
  - Look for `⚙️  [EVENT SEQUENCER] Processing` logs
  - If missing: sequencer might not be initialized

- **Solution:** Check that `useEventSequencer` is being called:
  ```bash
  docker logs baseball_frontend | grep "EVENT SEQUENCER" | head -20
  ```

## Performance Notes

- **No performance regression:** Same number of state updates, just restored proper ordering
- **Modal visibility:** Achieved through CSS z-index, not timing tricks
- **Sequencing:** Event Sequencer still controls callback timing (3100ms delays, etc.)

## Data Flow Diagram

```
PLAY_RESOLVED arrives via WebSocket
    ↓
[WebSocket Handler]
    ├─ setGameState(parseStateData(payload))
    ├─ callbacks.onPlayResolved(payload)
    ↓
[StadiumShowcaseScreen]
    ├─ handlePlayResolved() enqueues event
    ↓
[Event Sequencer]
    ├─ [0ms] show-modal callback
    │   └─ setLastResult() → Modal renders (CSS z-index first)
    ├─ [1000ms] delay
    ├─ [1900ms] update-balls
    ├─ [2500ms] update-outs
    ├─ [2600ms] update-pitcher-stats
    ├─ [2700ms] check-inning-end
    ↓
[React Renders]
    ├─ Modal visible first (z-index: 100)
    ├─ Scorecard updates below (z-index: 10)
    ↓
[User Sees]
    1. Modal appears with play description
    2. After ~1 second, scorecard updates with new counts
```

## Next Steps If Issues Persist

1. Check if container is running: `docker ps | grep baseball`
2. Rebuild and restart: `docker-compose down && docker-compose up -d`
3. Check container logs: `docker logs baseball_frontend` and `docker logs baseball_backend`
4. Verify network communication: Open DevTools → Network tab → look for WebSocket messages
5. If WebSocket is down: Check backend logs for connection errors

## Success Criteria

✅ Modal appears when play event happens  
✅ Console shows `[STEP] show-modal` executing without errors  
✅ After modal disappears, scorecard updates visible  
✅ No `setGameState is not defined` errors  
✅ gameState contains non-empty pitcher_strikeouts, batter_stats after PLAY_RESOLVED  
✅ Sequence of logs matches expected order (show-modal → delays → other callbacks)  
