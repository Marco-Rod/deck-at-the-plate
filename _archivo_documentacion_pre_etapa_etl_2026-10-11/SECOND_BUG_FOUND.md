# Second Bug Found: PlayResultOverlay Not Updating on Rapid Events

## The New Problem Identified

Even though the `showModalCallback` was being called correctly, `PlayResultOverlay` wasn't re-triggering for rapid consecutive events because the `resultTs` prop wasn't changing.

## Root Cause

In `useEventSequencerCallbacks.ts`, we were using:
```typescript
ts: Date.now()
```

**The problem:** If two events arrive within the same millisecond (which is common), `Date.now()` returns the same value. When `PlayResultOverlay` checks its dependency:

```typescript
useEffect(() => {
  if (!resultText || !resultTs) return;
  // Only re-runs when resultTs changes
  setTriggerCount(c => c + 1);
}, [resultTs]);
```

If `resultTs` is the same as before, the effect doesn't run, and `triggerCount` doesn't update. So `PlayResultOverlay` shows the old modal instead of the new one.

## The Fix Applied

Changed from timestamp-only to a counter-based ID:

```typescript
// Added ref for counter
const eventCounterRef = React.useRef(0);

// In showModalCallback:
eventCounterRef.current++;
const eventId = `${Date.now()}-${eventCounterRef.current}`;

const eventData = {
  ts: eventId,  // Always unique, even for rapid events
};
```

**Why this works:**
- Even if two events arrive at T=1000ms, they get IDs:
  - Event 1: `"1000-1"`
  - Event 2: `"1000-2"`
- `PlayResultOverlay` sees different `resultTs` values
- Effect re-runs every time
- `triggerCount` increments for every event

## Timeline

**Before (Bug):**
```
T=1000ms: Event 1 → ts: 1000 → PlayResultOverlay updates ✅
T=1001ms: Event 2 → ts: 1001 → PlayResultOverlay updates ✅
T=1002ms: Event 3 → ts: 1002 → PlayResultOverlay updates ✅
T=2000ms: Event 4 → ts: 2000 (same millisecond window potentially?)
T=2000ms: Event 5 → ts: 2000 (SAME as Event 4!) ❌
           PlayResultOverlay doesn't re-trigger, uses old data
```

**After (Fixed):**
```
T=1000ms: Event 1 → ts: "1000-1" → PlayResultOverlay updates ✅
T=1001ms: Event 2 → ts: "1001-2" → PlayResultOverlay updates ✅
T=1002ms: Event 3 → ts: "1002-3" → PlayResultOverlay updates ✅
T=2000ms: Event 4 → ts: "2000-4" → PlayResultOverlay updates ✅
T=2000ms: Event 5 → ts: "2000-5" → PlayResultOverlay updates ✅ (different ID!)
```

## Files Modified

**`frontend/src/hooks/useEventSequencerCallbacks.ts`**
- Added `eventCounterRef` at top of hook
- Changed `ts` from `Date.now()` to `${Date.now()}-${eventCounterRef.current}`

## How to Verify

In `PlayResultOverlay` console logs, you should now see:
```
📥 [PlayResultOverlay] Received new event data: { resultEvent: 'STRIKE_SWINGING', resultText: '...', resultTs: '1000-1' }
📈 triggerCount before: 0 → incrementing
📈 triggerCount after: 1

📥 [PlayResultOverlay] Received new event data: { resultEvent: 'HIT_1B', resultText: '...', resultTs: '1001-2' }
📈 triggerCount before: 1 → incrementing
📈 triggerCount after: 2
```

Each `resultTs` should be unique, and `triggerCount` should increment for every event.

## Expected Result

- Modal now appears for EVERY event
- No more disappearing modals
- Works correctly even for rapid consecutive events
