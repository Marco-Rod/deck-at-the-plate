# Testing Instructions for Modal Disappearing Bug Fix

## Quick Test Checklist

### Before Running
1. Ensure Docker container is clean (no cached builds)
2. Check that you see NO TypeScript errors in `npm run build`
3. Verify the three modified files have correct syntax:
   - `frontend/src/hooks/useEventSequencer.ts`
   - `frontend/src/hooks/useEventSequencerCallbacks.ts`
   - `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`

### Step 1: Start Game
1. Open browser DevTools (F12)
2. Go to Console tab
3. Start a new game (choose team, select lineup, etc.)
4. Look for console output like:
   ```
   📌 [REGISTER STEP] Registering callback for step: show-modal
   📌 [REGISTER STEP] Registering callback for step: close-modal
   ... (more steps)
   ✅ Step "show-modal" now has callback. Total steps registered: 11
   ```

### Step 2: First Event (HOME_RUN typically)
Watch for this exact sequence in console:
```
⚙️  [EVENT SEQUENCER] Processing event: HOME_RUN (id: 1234567-abc...)
   🕐 Event sequence starting at T=1234567890

  📍 [STEP] show-modal (delay: 0ms) - executing callback
    🎬 [SHOW-MODAL] Event: HOME_RUN
    → Setting isModalVisible to TRUE
    → Setting modalEventData: {text: "HOME RUN!", event: "HOME_RUN", ts: 1234567890}
    📊 [STADIUM] isModalVisible STATE CHANGED: {
      isModalVisible: true,
      modalEventData: "HOME_RUN",
      deferredGameState: <current inning>
    }
    ✅ show-modal completed in Xms

  📍 [STEP] update-score (delay: 3600ms)
    ...

  📍 [STEP] close-modal (delay: 4100ms) - executing callback
    🚪 [CLOSE-MODAL] Closing modal
    → Setting isModalVisible to FALSE
    → Setting deferredGameState to NULL
    📊 [STADIUM] isModalVisible STATE CHANGED: {
      isModalVisible: false,
      modalEventData: "HOME_RUN",  ← Should STILL have the event data
      deferredGameState: null
    }
    ✅ close-modal completed in Xms

✅ [EVENT SEQUENCER] Event completed: HOME_RUN
```

### Step 3: Repeat Events (Critical Test)
1. Play until you see a BALL event
2. Let it happen 3-4 times
3. For each occurrence, verify the EXACT same log pattern appears:
   ```
   ⚙️  [EVENT SEQUENCER] Processing event: BALL
   ...
   🎬 [SHOW-MODAL] Event: BALL
   → Setting isModalVisible to TRUE
   ...
   🚪 [CLOSE-MODAL] Closing modal
   → Setting isModalVisible to FALSE
   ```

4. **CRITICAL**: If you see on the 3rd or 4th BALL:
   - **Missing**: `🎬 [SHOW-MODAL]` → Modal callback not firing
   - **Missing**: `📍 [STEP] show-modal` → Step not executing
   - **Missing**: `📊 [STADIUM] isModalVisible STATE CHANGED` → State not updating
   
   Then there's still a bug to investigate.

### Step 4: Visual Verification
1. Play the game naturally
2. After each event (15+ events total), verify:
   - ✅ Modal appears in center of screen
   - ✅ Modal shows correct text (e.g., "HOME RUN!", "STRIKE", "BALL")
   - ✅ Modal color/theme changes per event
   - ✅ Modal disappears after animation completes
   - ✅ Game continues with updated state

3. **FAIL conditions**:
   - Modal doesn't appear for some events
   - Modal appears but game is frozen
   - Modal appears for event #1 but not #2 of same type
   - Console shows no error but modal doesn't render

### Step 5: Edge Cases
1. **Rapid Clicking**: If possible, trigger multiple actions quickly
   - Verify queue still processes all events in order
   - Check console for event IDs: should be sequential

2. **Same Event Type Repeated**: 
   - Play until 3x STRIKE happens consecutively
   - Verify modal appears all 3 times
   - Look for log: each should have unique `ts` timestamp

3. **Different Events in Sequence**:
   - HOME_RUN → BALL → STRIKE sequence
   - Verify queue order is maintained in console:
     ```
     ✅ Event completed: HOME_RUN
     ⚙️  [EVENT SEQUENCER] Processing event: BALL  ← Immediately after
     ...
     ✅ Event completed: BALL
     ⚙️  [EVENT SEQUENCER] Processing event: STRIKE  ← Immediately after
     ```

## Debugging If Still Broken

### Check 1: No Callbacks Registered
**Problem**: You see `Total steps registered: 0`

**Solution**: 
- Check that `useEventSequencerCallbacks` is being called
- Add log in `onStep`: `console.log('onStep called with:', stepName)`
- Verify `StadiumShowcaseScreen` line 107 is calling it correctly

### Check 2: Show-Modal Not Firing
**Problem**: `⚙️ Processing event:` appears but no `🎬 [SHOW-MODAL]`

**Solution**:
- Check that `step.delay` for show-modal is 0 (line 51 in useEventSequencer.ts)
- Check if callback is registered: search console for `REGISTER STEP` for `show-modal`
- Add breakpoint in `showModalCallback` in DevTools

### Check 3: isModalVisible Not Changing
**Problem**: `🎬 [SHOW-MODAL]` appears but `📊 [STADIUM]` shows `isModalVisible: false`

**Solution**:
- React state update might be batched weirdly
- Try adding a `key={modalEventData?.ts}` to PlayResultOverlay component
- Check if there's another useEffect resetting isModalVisible

### Check 4: Modal Rendering But Not Visible
**Problem**: PlayResultOverlay renders but doesn't appear on screen

**Solution**:
- Check browser DevTools Elements: find PlayResultOverlay in DOM
- Check if z-index is correct (should be 30-40)
- Check if opacity is 0 or display: none
- Check if parent container has `overflow: hidden`

## Critical Logs to Monitor

Print these patterns and watch for their frequency:

| Pattern | Healthy | Unhealthy |
|---------|---------|-----------|
| `⚙️ [EVENT SEQUENCER] Processing` | 1 per event | Should NOT see 2 in a row (no concurrency) |
| `🎬 [SHOW-MODAL]` | 1 per event | Should equal number of events processed |
| `🚪 [CLOSE-MODAL]` | 1 per event | Should equal number of events processed |
| `✅ [EVENT SEQUENCER] Event completed` | 1 per event | Should follow close-modal |
| `📊 [STADIUM] isModalVisible STATE CHANGED` | 2 per event (true→false) | Should alternate |

## Report Template

If the bug persists, collect:

1. Screenshot of console showing 15+ consecutive events
2. Count how many events show `🎬 [SHOW-MODAL]` vs total events
3. Note the event number where modal stops appearing
4. Check if it's always the same event type or random
5. Full console output around the point where modal stops

Then the next iteration can focus on exactly where the sequencer breaks down.
