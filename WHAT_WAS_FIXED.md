# What Was Fixed - Concise Summary

## The Problem
**Symptom:** Modal appears on the first event, then stops appearing on all subsequent events. The UI keeps updating (so WebSocket works), but modals just don't render.

**In your test:** STRIKE_SWINGING showed modal, but HIT_1B didn't. Same for BALL after that.

## The Root Cause
In `useEventSequencerCallbacks.ts`, the `showModalCallback` had `gameState` as a dependency:

```typescript
// ❌ OLD CODE
const showModalCallback = useCallback((payload) => {
  // callback code
}, [..., gameState]);  // gameState as dependency
```

**The problem chain:**
1. First event processes → callback works
2. WebSocket updates gameState (score changed, strikes changed, etc.)
3. React detects gameState reference changed
4. React RECREATES showModalCallback as a completely new function
5. useEffect sees the new callback reference and re-registers it
6. **BUT** the second event's setTimeout was already scheduled with the OLD callback reference
7. When setTimeout fires, it can't find or execute the old callback properly
8. Modal doesn't appear

## The Solution
Use a **ref** to store gameState instead of making it a dependency:

```typescript
// ✅ NEW CODE
const gameStateRef = React.useRef(gameState);

React.useEffect(() => {
  gameStateRef.current = gameState;  // Update ref when state changes
}, [gameState]);

const showModalCallback = useCallback((payload) => {
  setDeferredGameState(gameStateRef.current);  // Read from ref
}, [...]);  // NO gameState in dependencies!
```

**Why this works:**
- Callback is created ONCE and never recreated
- WebSocket updates just update the ref, not the callback
- ref always contains current gameState
- Callback reference stays stable, events can execute it
- Modal appears for all events

## What Actually Changed

**File:** `frontend/src/hooks/useEventSequencerCallbacks.ts`

**Lines added (after line 18):**
```typescript
// Guardar gameState en un ref para que pueda ser accedido sin ser una dependencia
const gameStateRef = React.useRef(gameState);

// Actualizar el ref cuando gameState cambia, pero no causa re-renders
React.useEffect(() => {
  gameStateRef.current = gameState;
}, [gameState]);
```

**Line changed:**
```typescript
// OLD: setDeferredGameState(gameState);
// NEW: setDeferredGameState(gameStateRef.current);
```

**Dependency array changed:**
```typescript
// OLD: }, [setIsModalVisible, setDeferredGameState, setModalEventData, setIsAwaitingResult, gameState]);
// NEW: }, [setIsModalVisible, setDeferredGameState, setModalEventData, setIsAwaitingResult]);
//        ↑ removed gameState
```

## Before vs After

### Before (Broken)
```
Event 1: 🎬 [SHOW-MODAL] ✅
WebSocket: gameState updates
Event 2: ❌ No modal (callback recreated, reference lost)
Event 3: ❌ No modal
Event 4+: ❌ No modals
```

### After (Fixed)
```
Event 1: 🎬 [SHOW-MODAL] ✅
WebSocket: gameState updates (ref updated, callback unchanged)
Event 2: 🎬 [SHOW-MODAL] ✅
Event 3: 🎬 [SHOW-MODAL] ✅
Event 4+: 🎬 [SHOW-MODAL] ✅ (all events work)
```

## How to Verify It Works

In browser console during game:
1. Look for `🎬 [SHOW-MODAL]` log
2. It should appear for **EVERY** event you play
3. If you see it only for event #1, the fix didn't apply

Expected pattern:
```
⚙️ [EVENT SEQUENCER] Processing event: STRIKE_SWINGING
  📍 [STEP] show-modal
    🎬 [SHOW-MODAL] Event: STRIKE_SWINGING

⚙️ [EVENT SEQUENCER] Processing event: HIT_1B
  📍 [STEP] show-modal
    🎬 [SHOW-MODAL] Event: HIT_1B  ← MUST APPEAR

⚙️ [EVENT SEQUENCER] Processing event: BALL
  📍 [STEP] show-modal
    🎬 [SHOW-MODAL] Event: BALL  ← MUST APPEAR
```

## Technical Explanation (Optional)

**React Hooks Pattern Issue:**
- When you include a frequently-changing value in useCallback dependencies, the callback recreates every time that value changes
- Recreating the callback breaks any external registrations (like in a ref that expects the callback to be stable)
- **Solution:** Use useRef to store the value and read it from the ref instead of depending on it

**This is a well-known React pattern** used when you need:
- Stable function reference (for event listeners, callbacks, registrations)
- But access to current/fresh data

**Real-world analogy:**
- OLD: You write down a phone number to call. But every time the person changes phones, you need a new note.
- NEW: You write down an address. The address never changes, but inside that address lives the person who updates their own phone number.

## Status

✅ **Fix Applied**
- File modified: `frontend/src/hooks/useEventSequencerCallbacks.ts`
- Change type: Dependency management (useRef pattern)
- Risk level: Low (isolated change, well-established pattern)
- Backward compatible: Yes

**Next step:** Test in Docker and verify modals appear for all events.
