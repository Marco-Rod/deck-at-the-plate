# Two-Layer Bug Analysis: Modal Disappearing

The modal disappearing bug was actually **TWO separate bugs** stacked on top of each other:

## Layer 1: Callback Recreation Bug (Fixed First)

**Location:** `useEventSequencerCallbacks.ts`

**Problem:** 
- `gameState` was a dependency of `showModalCallback`
- WebSocket updated gameState
- `useCallback` detected change and recreated the callback
- Event sequencer lost reference to old callback
- Callbacks stopped executing for events after the first

**Symptom:** Modal appears for event #1, disappears for #2

**Fix:** Use `useRef` pattern to read state without depending on it

---

## Layer 2: Event ID Uniqueness Bug (Found During Testing)

**Location:** `useEventSequencerCallbacks.ts` + `PlayResultOverlay.tsx`

**Problem:**
- Modal event data uses `ts: Date.now()` as the unique identifier
- `PlayResultOverlay` depends on this `resultTs` changing to re-trigger
- When two events arrive in the same millisecond, `Date.now()` returns the same value
- `PlayResultOverlay`'s useEffect doesn't re-run (no dependency change)
- Modal shows old data instead of new event

**Symptom:** Modal disappears after X events (when timing causes collisions)

**Fix:** Use `counter + timestamp` to guarantee uniqueness

---

## The Complete Bug Chain

```
Event 1 Arrives (STRIKE_SWINGING)
  ↓
Backend sends PLAY_RESOLVED
  ↓
Frontend enqueues: STRIKE_SWINGING
  ↓
Event Sequencer processes:
  - show-modal step calls showModalCallback
  - showModalCallback sets modalEventData with ts: "1000-1"
  ↓
PlayResultOverlay sees new resultTs
  - triggerCount increments
  - visible = true
  - Modal appears ✅

Meanwhile: WebSocket updates gameState (score changed)
  - [BUG 1 HERE] Old fix prevented callback recreation
  
Event 2 Arrives (HIT_1B) 
  - Arrives at T=1000ms (same millisecond!)
  ↓
Event Sequencer processes:
  - show-modal step calls showModalCallback
  - showModalCallback sets modalEventData with ts: "1000-1" (SAME!)
  ↓
PlayResultOverlay compares:
  - Old resultTs: "1000-1"
  - New resultTs: "1000-1"
  - SAME VALUE! useEffect doesn't re-run ❌
  - [BUG 2 HERE] triggerCount doesn't increment
  - visible stays false
  - Modal doesn't appear ❌

Event 3+: Same problem repeats
```

## Solution: Two-Layer Fix

### Fix 1: Callback Stability (useRef Pattern)
```typescript
const gameStateRef = React.useRef(gameState);
React.useEffect(() => {
  gameStateRef.current = gameState;
}, [gameState]);

const showModalCallback = useCallback((payload) => {
  setDeferredGameState(gameStateRef.current);  // Read from ref
}, [...]);  // NO gameState in dependencies
```

### Fix 2: Event ID Uniqueness (Counter-Based)
```typescript
const eventCounterRef = React.useRef(0);

const showModalCallback = useCallback((payload) => {
  eventCounterRef.current++;
  const eventId = `${Date.now()}-${eventCounterRef.current}`;
  
  const eventData = {
    ts: eventId,  // Always unique!
  };
}, [...]);
```

## Why Both Fixes Are Necessary

**If only Fix 1 (callback stability):**
- Callbacks execute correctly
- But `PlayResultOverlay` doesn't update for rapid events
- Modal appears then gets stuck

**If only Fix 2 (unique IDs):**
- `PlayResultOverlay` re-triggers for every event
- But if callbacks are recreated (gameState dependency), they won't execute
- Modal condition is met but callback never fires

**With Both Fixes:**
- Callbacks always execute (Fix 1)
- `PlayResultOverlay` always updates (Fix 2)
- Modal works reliably

## Testing to Confirm

Run this sequence to verify both fixes:

1. **Rapid single-type events** (test for duplicate timestamps):
   - Throw 3 consecutive BALL events
   - All 3 should show modals
   - Check console: each should have unique `ts` like "1000-1", "1000-2", "1000-3"

2. **Mixed events** (test for callback recreation):
   - Throw STRIKE, then HIT, then BALL
   - All should show modals
   - Check console: no "lost callback" warnings

3. **Extended gameplay** (test for accumulation issues):
   - Play 30+ events
   - Modal should continue appearing consistently
   - No degradation over time

## Key Insights

1. **Millisecond collisions are real:** When events process quickly, `Date.now()` returns the same value
2. **React dependency tracking is strict:** Even `Date.now()` needs to be unique to trigger effects
3. **Callback registration is fragile:** State dependencies can cause cascading recreation cycles
4. **Multiple layers of bugs:** Sometimes one fix reveals the next layer

## Prevention

For future modal/event systems:

1. **Always use unique IDs** - never rely on timing alone
2. **Avoid state dependencies in callbacks** - use refs for read-only access
3. **Test with rapid events** - don't just test manual clicking
4. **Monitor callback references** - ensure registration doesn't change unexpectedly
