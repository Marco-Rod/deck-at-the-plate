# Fix: Modal Callbacks Losing Registration After First Event

## The Problem (In Detail)

When `gameState` is included as a dependency in `useCallback`:

```typescript
const showModalCallback = useCallback((payload) => {
  // ... show modal logic ...
}, [..., gameState]);  // ❌ PROBLEM: gameState changes constantly
```

**What happens:**

1. **First event (STRIKE_SWINGING):**
   - Hook initializes
   - `useEventSequencerCallbacks` runs
   - `showModalCallback` created with current `gameState`
   - `useEffect` registers it: `onStep('show-modal', showModalCallback)` 
   - Callback stored in `stepCallbacksRef.current.set('show-modal', <callback_v1>)`
   - Event processes, modal appears ✅

2. **WebSocket updates gameState:**
   - New score, new pitcher, new strikes/balls, etc.
   - `gameState` object changes (new reference)
   - React detects dependency change in `useCallback`
   - **`showModalCallback` is recreated as a NEW function** (different memory reference)

3. **useEffect with showModalCallback dependency:**
   - Sees that `showModalCallback` reference changed
   - Re-runs: `onStep('show-modal', <callback_v2>)`
   - **Overwrites** the previous callback: `stepCallbacksRef.current.set('show-modal', <callback_v2>)`

4. **Meanwhile, second event (HIT_1B) is queued:**
   - Event's `show-modal` step setTimeout is scheduled for T+0ms
   - But it's scheduled in a `forEach` loop that already captured the **old callback reference**
   - By the time the setTimeout fires (0ms later), the callback has been replaced!

5. **When step executes:**
   ```typescript
   setTimeout(() => {
     const callback = stepCallbacksRef.current.get('show-modal');  // Gets <callback_v2>
     if (callback) {
       callback(event.payload);  // Calls NEW callback, but timing is wrong
     }
   }, 0);
   ```

The timing mismatch is **brutal**:
- Step timer scheduled with old callback reference
- Callback changed in `stepCallbacksRef` before timer fires
- **New callback might have stale closure variables or different behavior**

## The Solution: useRef Instead of Dependency

```typescript
// ✅ CORRECT APPROACH
const gameStateRef = React.useRef(gameState);

React.useEffect(() => {
  gameStateRef.current = gameState;  // Update ref WITHOUT changing dependency
}, [gameState]);

const showModalCallback = useCallback((payload) => {
  setDeferredGameState(gameStateRef.current);  // Use REF, not dependency
}, [setIsModalVisible, setDeferredGameState, setModalEventData, setIsAwaitingResult]);
// ⬆️ gameState NOT in dependencies - callback never re-creates!
```

**Why this works:**

1. **`showModalCallback` is created ONCE** when component mounts
2. **Stored in `stepCallbacksRef`** and never changes
3. **Whenever it's called**, it reads the current value from `gameStateRef.current`
4. **`gameStateRef.current` is updated** every time `gameState` changes (via the effect)
5. **But the callback reference stays the same** - React doesn't recreate it

**Timeline with this fix:**

```
1. Component mounts
   → createCallback showModalCallback (v1) 
   → register: stepCallbacksRef.set('show-modal', v1)

2. Event 1 (STRIKE_SWINGING) processes
   → Schedule setTimeout for 'show-modal'
   → step.callback = stepCallbacksRef.get('show-modal')  // Gets v1 ✅
   → Executes v1, reads gameStateRef.current (whatever is current)

3. WebSocket sends score update
   → gameState changes
   → useEffect([gameState]) runs
   → gameStateRef.current = gameState  (just updates ref, doesn't recreate callback)
   → showModalCallback NOT recreated!

4. Event 2 (HIT_1B) processes  
   → Schedule setTimeout for 'show-modal'
   → step.callback = stepCallbacksRef.get('show-modal')  // Still v1 ✅
   → Executes v1, reads gameStateRef.current (the NEW state from step 3)

5. Event 3, 4, 5... all work the same way
   → Callback reference NEVER changes
   → Registration in stepCallbacksRef NEVER changes
   → But callback always reads fresh data from ref
```

## Why This Pattern Works for React

**React's callback dependency tracking:**
- Primitive values (strings, numbers, booleans): compared by value
- Objects/functions: compared by reference
- When dependency changes, React assumes the callback might have different behavior
- So it re-runs effects that depend on it

**But with useRef:**
- Refs are mutable containers that don't trigger re-renders or effect re-runs
- Updating a ref does NOT change the ref object itself (just its `.current` property)
- So the effect dependency `[gameState]` can change, but the `useCallback` dependency array stays stable
- The callback never re-creates, never gets re-registered, always works

## Key Insight

**The fix separates two concerns:**
1. **Timing concern:** When the callback executes (determined by step.delay)
2. **Data concern:** What data the callback sees (via ref, not dependency)

By decoupling them:
- The callback's **execution schedule never changes**
- But the callback's **visible data is always current**

## Testing This Fix

In browser console, you should see:

```
Event 1 (STRIKE_SWINGING):
  🎬 [SHOW-MODAL] Event: STRIKE_SWINGING
  → Freezing gameState via deferredGameState
  ✅ modal appears

WebSocket: gameState updated
  (no log about callback changing - that's good!)

Event 2 (HIT_1B):
  🎬 [SHOW-MODAL] Event: HIT_1B
  → Freezing gameState via deferredGameState
  ✅ modal appears

Event 3, 4, 5... all show modals correctly
  (consistency maintained across all events)
```

If you see the callback registration logs appearing for every event, that means the callback is being recreated (bad - old bug). With this fix, you should see callback registration only once per game session.
