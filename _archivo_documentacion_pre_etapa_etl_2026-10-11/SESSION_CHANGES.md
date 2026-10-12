# Session Changes: Modal Disappearing Bug - Final Fix

## Problem Statement
Modal was disappearing after the first event or when WebSocket updates occurred. Events 2+ would be processed but modals wouldn't appear.

## Root Cause Identified
**WebSocket dependency chain:**
1. Backend sends game state update via WebSocket
2. Frontend receives PLAY_RESOLVED event
3. `gameState` prop updates in StadiumShowcaseScreen
4. `useEventSequencerCallbacks` receives new `gameState`
5. `showModalCallback` useCallback has `gameState` as dependency
6. `showModalCallback` recreates as new function reference
7. `useEffect([..., showModalCallback])` detects change
8. **Re-registers callback in stepCallbacksRef**
9. **But timing is wrong:** next event's setTimeout might already have captured old reference
10. Modal callback lookup fails or executes with stale data

## Files Modified This Session

### 1. `frontend/src/hooks/useEventSequencerCallbacks.ts`
**Before:**
```typescript
const showModalCallback = useCallback((payload) => {
  setIsModalVisible(true);
  setDeferredGameState(gameState);  // ❌ gameState dependency
  // ...
}, [..., gameState]);  // ❌ Recreates on every WebSocket update
```

**After:**
```typescript
const gameStateRef = React.useRef(gameState);

React.useEffect(() => {
  gameStateRef.current = gameState;  // Update ref WITHOUT dependency change
}, [gameState]);

const showModalCallback = useCallback((payload) => {
  setIsModalVisible(true);
  setDeferredGameState(gameStateRef.current);  // ✅ Read from ref
  // ...
}, [setIsModalVisible, setDeferredGameState, setModalEventData, setIsAwaitingResult]);
// ✅ NO gameState in dependencies - never recreates!
```

**Why:** 
- Callback created once when component mounts
- Never recreates, stays registered in stepCallbacksRef
- But always reads current gameState via ref
- Separates execution schedule (fixed) from data freshness (current)

### 2. `frontend/src/hooks/useEventSequencer.ts`
**Changes:**
- Moved `EVENT_SEQUENCES` to module level as `EVENT_SEQUENCES_STABLE` (constant, never changes)
- Changed useEffect deps from `[queue]` to `[queue.length, isProcessing]` (primitives trigger reliably)
- Added `setIsProcessing(true)` at event start, `setIsProcessing(false)` at end
- Added logging: `📌 [REGISTER STEP]` with callback count

**Why:**
- Prevents useEffect from re-running when EVENT_SEQUENCES re-created
- Primitive dependencies (length, boolean) are more reliable than object comparison
- State-based tracking (isProcessing) guarantees React knows when to re-trigger

### 3. `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`
**Changes:**
- Added monitoring useEffect for isModalVisible state changes
- Added console.log checks for render condition failures
- Logging shows when modal is NOT rendered and why

**Why:**
- Visibility into when and why modal fails to render
- Helps identify if it's state not updating vs component not rendering

## How The Fix Works

**The useRef pattern solves the dependency problem:**

```javascript
// ❌ OLD - Problematic
useCallback(() => {
  doSomething(gameState);  // uses gameState parameter
}, [gameState]);  // recreates when gameState changes

// ✅ NEW - Fixed
const ref = useRef(gameState);
useEffect(() => { ref.current = gameState; }, [gameState]);
useCallback(() => {
  doSomething(ref.current);  // uses ref (never changes)
}, []);  // never recreates!
```

**Why this solves the WebSocket timing issue:**

1. **Callback reference is stable** → always found in stepCallbacksRef
2. **Can be scheduled in setTimeout** → and still execute the same callback later
3. **Reads current data via ref** → gets fresh gameState every time
4. **No race condition** → callback registration never competes with event processing

## Expected Behavior After Fix

### Event Processing Flow (Corrected)
1. WebSocket event arrives
2. `enqueueEvent()` adds to queue
3. useEffect detects `queue.length` changed
4. `setIsProcessing(true)` triggers processing
5. All step timers scheduled (with STABLE callback references)
6. Each step executes:
   - `show-modal` callback executes → reads current gameState from ref → sets modalEventData
   - Other steps execute...
   - `close-modal` callback executes → clears modalEventData
7. Event completes, `setIsProcessing(false)` → next event can start
8. **Process repeats for events 2, 3, 4...** without losing callbacks

### Console Log Pattern (Should See)
```
⚙️ [EVENT SEQUENCER] Processing event: STRIKE_SWINGING
  📍 [STEP] show-modal (delay: 0ms)
    🎬 [SHOW-MODAL] Event: STRIKE_SWINGING
    → Freezing gameState via deferredGameState
✅ [EVENT SEQUENCER] Event completed: STRIKE_SWINGING

⚙️ [EVENT SEQUENCER] Processing event: HIT_1B  ← IMMEDIATELY FOLLOWS
  📍 [STEP] show-modal (delay: 0ms)
    🎬 [SHOW-MODAL] Event: HIT_1B  ← Must appear for every event
    → Freezing gameState via deferredGameState
✅ [EVENT SEQUENCER] Event completed: HIT_1B

⚙️ [EVENT SEQUENCER] Processing event: BALL
  📍 [STEP] show-modal (delay: 0ms)
    🎬 [SHOW-MODAL] Event: BALL  ← Even for repeated event types
    → Freezing gameState via deferredGameState
```

**Critical indicator:** `🎬 [SHOW-MODAL]` log should appear for EVERY event, not disappear after #1 or #2.

## Testing Checklist

- [ ] Game loads without errors
- [ ] First event shows modal ✅
- [ ] Second event shows modal ✅ (THIS WAS FAILING BEFORE)
- [ ] Multiple events in sequence show modals ✅
- [ ] WebSocket updates don't break modal display
- [ ] Repeated event types (BALL, BALL, BALL) all show modals
- [ ] Modal appears at event ~20+ (was breaking at ~14-15)
- [ ] Console has no `❌ [STADIUM] Modal NOT rendered` logs after first event

## Rollback Info

If this doesn't fix it, the problem is deeper (likely in PlayResultOverlay or event payload structure):

**Previous attempted solutions:**
1. ✅ Fixed: useEffect deps [queue] → [queue.length, isProcessing]
2. ✅ Fixed: EVENT_SEQUENCES constant at module level
3. ✅ Fixed: gameState dependency in useCallback with useRef pattern

**If still broken, check:**
- PlayResultOverlay.tsx triggerCount/visible state logic
- Event name normalization (is BALL coming as "BALL" or something else?)
- WebSocket message structure (is payload.event correct?)
- Browser DevTools React Profiler for unexpected re-renders
