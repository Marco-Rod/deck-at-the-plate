# Troubleshooting: If Modal Bug Persists

This guide helps diagnose if the fix worked or if the problem has a different root cause.

## Step 1: Verify Fix Was Applied

### Check the Code
Open `frontend/src/hooks/useEventSequencerCallbacks.ts` and verify:

1. **Lines 20-25 exist:**
```typescript
const gameStateRef = React.useRef(gameState);

React.useEffect(() => {
  gameStateRef.current = gameState;
}, [gameState]);
```

2. **Line ~37 has:**
```typescript
setDeferredGameState(gameStateRef.current);  // NOT setDeferredGameState(gameState)
```

3. **Line ~46 dependency array:**
```typescript
}, [setIsModalVisible, setDeferredGameState, setModalEventData, setIsAwaitingResult]);
// NO gameState in here
```

**If any of these are missing:** The fix wasn't applied. Apply it manually.

## Step 2: Check Console Logs

### Healthy Pattern (Fix Working)
```
Event 1:
  ⚙️ [EVENT SEQUENCER] Processing event: STRIKE_SWINGING
  📍 [STEP] show-modal (delay: 0ms)
  🎬 [SHOW-MODAL] Event: STRIKE_SWINGING ✅

Event 2:
  ⚙️ [EVENT SEQUENCER] Processing event: HIT_1B
  📍 [STEP] show-modal (delay: 0ms)
  🎬 [SHOW-MODAL] Event: HIT_1B ✅

Event 3+: Same pattern continues ✅
```

### Unhealthy Pattern #1 (First Fix Didn't Work)
```
Event 1:
  ⚙️ [EVENT SEQUENCER] Processing event: STRIKE_SWINGING
  📍 [STEP] show-modal (delay: 0ms)
  🎬 [SHOW-MODAL] Event: STRIKE_SWINGING ✅

Event 2:
  ⚙️ [EVENT SEQUENCER] Processing event: HIT_1B
  (NO 📍 [STEP] show-modal log)
  (NO 🎬 [SHOW-MODAL] log) ❌

Solution: Go back to Step 1, verify fix is exactly as shown
```

### Unhealthy Pattern #2 (No Callbacks Registered)
```
(No 📌 [REGISTER STEP] logs at all)
(Events process but no step callbacks fire)

Solution: Check that useEventSequencerCallbacks is being called from StadiumShowcaseScreen
```

## Step 3: Visual Diagnosis

### If Console Logs Look Good But Modal Doesn't Appear

Check if PlayResultOverlay has issues:

1. **Open browser DevTools → Elements**
2. **Search for `PlayResultOverlay`**
3. **Check if element is in DOM**

```javascript
// In console, paste:
document.querySelector('[data-testid="play-result-overlay"]')
// or search for any div with "Modal" or "Overlay" class
```

If element exists in DOM:
- Check CSS: `visibility`, `display`, `opacity`
- Modal might be rendered but hidden by styling

If element doesn't exist in DOM:
- Check if condition `{isModalVisible && modalEventData &&}` is true
- Check browser console for errors

## Step 4: Check Event Payload

Events might not be arriving correctly:

### In Console, Log Events
Add this to `frontend/src/components/stadium/StadiumShowcaseScreen.tsx` line ~72:

```typescript
console.log('🔍 [DEBUG] Enqueuing event:', {
  original,
  normalized,
  payload: enqueueEvent // the payload being sent
});
```

Check if `payload` has:
- `event` property (STRIKE_SWINGING, etc.)
- `description` property (the text to show)
- Any other expected data

If payload is empty or malformed:
- Problem is in WebSocket or event parsing
- Not related to the modal callback fix

## Step 5: Check if WebSocket Is Connected

```javascript
// In browser console:
// Find useStadiumSocket hook instance
// Check logs for:
console.log('[WS] Conectado exitosamente');  // Should appear once

// If WebSocket isn't connected:
// Look for: WebSocket connection error
```

If WebSocket isn't connected:
- Events won't arrive
- This is a different issue than modal callback

## Step 6: Rebuild and Clear Cache

Sometimes Docker caches compiled code:

```bash
# In Docker terminal:
docker-compose down
docker-compose up --build

# In browser:
- Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Or: Ctrl+Shift+Delete to open Clear Cache dialog
```

## Step 7: Check for TypeScript Errors

```bash
cd frontend
npm run build  # or yarn build
```

If you see TypeScript errors, the code might not have compiled correctly.

Look for errors related to:
- `useCallback`
- `useEffect`
- `useRef`
- `gameStateRef`

## Debug Checklist

Use this if modal still doesn't appear:

- [ ] Fix code is exactly as shown in QUICK_START_FIX.md
- [ ] Browser console shows `🎬 [SHOW-MODAL]` for events #1, #2, #3+
- [ ] No `❌ [STADIUM] Modal NOT rendered` errors in console
- [ ] PlayResultOverlay element exists in DOM
- [ ] PlayResultOverlay CSS doesn't hide it (opacity, display, z-index)
- [ ] WebSocket is connected (look for connection success log)
- [ ] Events are arriving (check payload in console)
- [ ] No TypeScript compilation errors
- [ ] Browser cache cleared and page hard-refreshed
- [ ] Docker container rebuilt clean

## If Still Not Working

Follow this order:

### 1. Most Likely (70% probability)
**PlayResultOverlay component issue:**
- Add console.log in PlayResultOverlay.tsx render
- Check if component's `visible` state is updating
- Look for: `🎬 [PlayResultOverlay] Modal is now VISIBLE`
- If missing: PlayResultOverlay isn't setting visible=true

**Solution:** Debug PlayResultOverlay.tsx triggerCount logic

### 2. Moderately Likely (20% probability)
**Event normalization issue:**
- Check if event names are being normalized correctly
- Look for: `🎯 [ENQUEUE EVENT] original="STRIKE_SWINGING" → normalized="STRIKE_SWINGING"`
- If normalized to something unexpected: check EVENT_SEQUENCES has that name

**Solution:** Add logging to event normalizer, check EVENT_SEQUENCES mappings

### 3. Less Likely (10% probability)
**Event payload structure issue:**
- Backend might be sending different event structure
- Check WebSocket message: `🔵 [FRONTEND] PLAY_RESOLVED received`
- Verify payload has correct shape

**Solution:** Compare expected vs actual payload structure

## Getting Help

If you're stuck, capture and share:

1. **Browser console output** (20+ events worth of logs)
2. **Screenshot of issue:** What you see on screen
3. **Steps to reproduce:** Exactly what you did
4. **Error messages:** Any red errors in console

This will help pinpoint where the issue is.

## Advanced: Network Inspection

If WebSocket events aren't arriving:

1. Open DevTools → Network tab
2. Filter by WS (WebSockets)
3. Click the WebSocket connection
4. Look at Messages tab
5. Verify PLAY_RESOLVED events are coming through

If you see PLAY_RESOLVED messages but modals don't appear:
- Problem is in frontend handling, not WebSocket

## Reference: Expected Log Timeline

```
0ms    - Component mounts
        → 📌 [REGISTER STEP] for all steps

100ms  - Game initialized, waiting for first event
        → No processing logs yet

2000ms - First pitch thrown
        → 🚀 [FRONTEND] Enviando pitch
        → ✅ [FRONTEND] Respuesta del servidor

2050ms - PLAY_RESOLVED received
        → 🔵 [FRONTEND] PLAY_RESOLVED received: STRIKE_SWINGING
        → 📤 [EVENT QUEUE] Enqueued: STRIKE_SWINGING
        → ⚙️ [EVENT SEQUENCER] Processing event: STRIKE_SWINGING
        → 📍 [STEP] show-modal
        → 🎬 [SHOW-MODAL] Event: STRIKE_SWINGING ✅
        → 🎬 [PlayResultOverlay] Modal is now VISIBLE

4100ms - Event completes
        → 🚪 [CLOSE-MODAL] Closing modal
        → 🎬 [PlayResultOverlay] Modal is now HIDDEN
        → ✅ [EVENT SEQUENCER] Event completed

4200ms - Ready for next pitch
        → (waiting for next event)
```

If your logs don't match this timeline, you've found where the issue is.
