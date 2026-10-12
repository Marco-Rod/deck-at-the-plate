# Quick Start: The Modal Bug Fix

## What Was Broken
Modal appears for the first event, then disappears for all subsequent events (even though the game continues updating).

## Root Cause in One Sentence
**`gameState` was a dependency of `showModalCallback`, causing the callback to be recreated every time WebSocket updated, which breaks the event sequencer's ability to find and execute it.**

## The Fix (One File)

**File:** `frontend/src/hooks/useEventSequencerCallbacks.ts`

### Change 1: Add useRef for gameState
At the top of the hook function, add:

```typescript
const gameStateRef = React.useRef(gameState);

React.useEffect(() => {
  gameStateRef.current = gameState;
}, [gameState]);
```

### Change 2: Update showModalCallback
**Find this:**
```typescript
const showModalCallback = useCallback((payload) => {
  console.log('🎬 [SHOW-MODAL] Event:', payload.event);
  console.log('   → Setting isModalVisible to TRUE');
  setIsModalVisible(true);
  setDeferredGameState(gameState);  // ← REMOVE THIS
  const eventData = {
    text: payload.description || payload.message || 'Evento',
    event: payload.event || 'UNKNOWN',
    ts: Date.now(),
  };
  console.log('   → Setting modalEventData:', eventData);
  setModalEventData(eventData);
  setIsAwaitingResult(true);
}, [setIsModalVisible, setDeferredGameState, setModalEventData, setIsAwaitingResult, gameState]);  // ← REMOVE gameState
```

**Replace with:**
```typescript
const showModalCallback = useCallback((payload) => {
  console.log('🎬 [SHOW-MODAL] Event:', payload.event);
  console.log('   → Setting isModalVisible to TRUE');
  setIsModalVisible(true);
  setDeferredGameState(gameStateRef.current);  // ← USE REF
  const eventData = {
    text: payload.description || payload.message || 'Evento',
    event: payload.event || 'UNKNOWN',
    ts: Date.now(),
  };
  console.log('   → Setting modalEventData:', eventData);
  setModalEventData(eventData);
  setIsAwaitingResult(true);
}, [setIsModalVisible, setDeferredGameState, setModalEventData, setIsAwaitingResult]);  // ← NO gameState
```

## Why This Works

- **Before:** Every time WebSocket updated `gameState`, the callback was recreated as a new function. The event sequencer couldn't find the old function in its registry.
- **After:** The callback is created once and never recreated. It reads current state from a ref instead of depending on it.

## How to Test

1. Start game in Docker
2. Play 10+ pitches
3. Look in browser console:
   - First event: You see `🎬 [SHOW-MODAL] Event: STRIKE_SWINGING`
   - Second event: You NOW SEE `🎬 [SHOW-MODAL] Event: HIT_1B` (THIS WAS MISSING BEFORE)
   - Third event+: You continue seeing `🎬 [SHOW-MODAL]` for every event

If you see the pattern continuing for events 1, 2, 3, 4... then it's fixed ✅

## Expected Result

Modal appears consistently for every event, including:
- Multiple events of the same type (BALL, BALL, BALL all show modals)
- Events after pitcher fatigue kicks in
- Events after game state has been updated many times

## If It Still Doesn't Work

The file might have been auto-formatted or there might be additional issues. Try:

1. Clear browser cache (hard refresh)
2. Rebuild Docker container
3. Check browser console for errors
4. Look for `❌ [STADIUM] Modal NOT rendered` logs - these indicate when the modal condition fails

If you see those, the problem is in PlayResultOverlay component or the event payload structure, not the fix.
