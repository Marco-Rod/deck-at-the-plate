# Immediate Actions to Test the Fix

## What Just Happened

I identified and fixed a critical bug where the code was trying to call `setGameState()` (a function that doesn't exist outside the hook) from the Event Sequencer callback. This caused the error:

```
ReferenceError: setGameState is not defined
```

And prevented the UI from updating after events.

## What Changed

Two files:
1. `frontend/src/hooks/useStadiumSocket.ts` - Restored state updates in WebSocket handlers
2. `frontend/src/components/stadium/StadiumShowcaseScreen.tsx` - Removed invalid function call

## To See the Fix in Action

### Step 1: Rebuild the Frontend Container (REQUIRED)
The container must rebuild to pick up the code changes.

```bash
# Option A: Full rebuild
docker-compose down
docker-compose up -d

# Option B: Just restart frontend (faster)
docker-compose restart frontend
```

**Wait 45-60 seconds** for Vite to rebuild and start.

### Step 2: Clear Browser Cache (CRITICAL)
The browser is likely serving cached JavaScript that has the old error.

**Windows:**
- Press: **Ctrl + Shift + R**

**Mac:**
- Press: **Cmd + Shift + R**

**Or manually:**
1. Open DevTools (F12)
2. Application tab → Storage → "Clear site data" → Clear

### Step 3: Hard Reload the Page
1. In DevTools console, should see no errors
2. Navigate to the game (localhost:5173)
3. Start a new game

### Step 4: Test an Event
1. Play a pitch
2. Batter swings
3. **Observe:**
   - ✅ Modal appears with play result
   - ✅ After modal, scorecard updates
   - ✅ Console shows `[STEP] show-modal` **without** an error

### Step 5: Check Console Logs
Press F12 → Console tab

**Look for (good signs):**
```
✅ [STEP] show-modal - Setting PlayResultOverlay
✅ [STEP] update-score - Actualizando scores
✅ [STEP] update-outs - Actualizando outs
```

**Look for (bad signs):**
```
❌ [STEP] Error in show-modal: ReferenceError: setGameState is not defined
```

## Expected Results

### Before Fix (What You Saw)
```
Error: setGameState is not defined
Modal might not appear
UI doesn't update
```

### After Fix (What You Should See)
```
✅ Modal appears immediately
✅ Console shows clean [STEP] logs
✅ Modal shows play description
✅ Scorecard updates after modal clears
✅ No errors in console
```

## Troubleshooting

### Problem: Still seeing the error
**Solution:**
1. Make sure container rebuilt: `docker ps | grep baseball_frontend`
2. If container wasn't rebuilt, restart: `docker-compose restart frontend`
3. Wait 60 seconds, then hard refresh browser
4. Check that line 283+ in StadiumShowcaseScreen.tsx has NO `setGameState` call

### Problem: Container won't rebuild
**Solution:**
```bash
# Force a full rebuild
docker-compose down -v
docker-compose up --build -d
```

Wait 2-3 minutes for everything to start.

### Problem: Still showing zeros for scores
**Solution:**
This is likely because no runs have been scored yet, or the scores legitimately are 0-0.
- Play more events (especially home runs, hits)
- Check if batter_stats are updating: filter console for `[PARSE_STATE_DATA]`
- If still all zeros after multiple hits: check backend logs

### Problem: Modal not appearing at all
**Solution:**
1. Check console for `✅ [STEP] show-modal` log
2. If missing: Event Sequencer not running
3. If present but no modal: CSS issue
4. Verify: `showGameIntro` is false (game has started)

## Quick Commands

```bash
# Check if containers are running
docker ps

# See frontend logs
docker logs baseball_frontend | tail -50

# See backend logs
docker logs baseball_backend | tail -50

# Restart everything
docker-compose restart

# Force full rebuild
docker-compose down -v && docker-compose up --build -d

# Open frontend shell (if needed)
docker exec -it baseball_frontend bash
```

## What NOT to Do

❌ Don't modify the files again - the fix is correct  
❌ Don't git commit yet - test first  
❌ Don't restart backend - it's unaffected  
❌ Don't clear Docker volumes unless needed  

## Timeline

- **Now:** Verify container is rebuilt and browser cache cleared
- **2 minutes:** Load game and test an event
- **5 minutes:** Check console logs for correct behavior
- **If working:** Mark as resolved and commit changes
- **If not working:** Run troubleshooting steps above

## Success Criteria Checklist

After following steps above, you should have:

- [ ] Container restarted/rebuilt
- [ ] Browser cache cleared
- [ ] Game loaded without errors
- [ ] Play an event
- [ ] Modal appeared
- [ ] Console shows ✅ [STEP] show-modal (no error)
- [ ] Scorecard updated after modal
- [ ] No `ReferenceError` in console

If all boxes are checked: **The fix works!**

## Next: Commit Changes

Once verified:
```bash
git add frontend/src/hooks/useStadiumSocket.ts
git add frontend/src/components/stadium/StadiumShowcaseScreen.tsx
git commit -m "fix: Restore WebSocket state updates, remove invalid setGameState call

- gameState should update immediately in useStadiumSocket hook
- Event Sequencer controls callback timing, not state updates
- CSS z-index ensures modal appears on top
- Fixes: ReferenceError: setGameState is not defined"
```

## Need Help?

- Read: `ROOT_CAUSE_ANALYSIS.md` - Why this happened
- Read: `FINAL_FIX_SUMMARY.md` - What was changed
- Read: `TESTING_SEQUENCING_FIX.md` - Detailed testing guide
