# Error Audit - Event Sequencer Implementation

## Critical Errors Found

### 1. useEventSequencer.ts - Line 161: Async setTimeout callback
**Severity:** HIGH - May cause unexpected behavior
**Issue:** 
```typescript
setTimeout(async () => {
  const callback = stepCallbacksRef.current.get(step.name);
  // ...
  await callback(event.payload, step.name);
}, step.delay);
```

**Problem:** `setTimeout` callback should be synchronous. Using `async` here doesn't actually wait for the promise to resolve before the next timer executes.

**Solution:**
```typescript
setTimeout(() => {
  const callback = stepCallbacksRef.current.get(step.name);
  if (callback) {
    // Don't await, just call and let it run
    Promise.resolve().then(() => callback(event.payload, step.name))
      .catch(err => console.error(`❌ [STEP] Error in ${step.name}:`, err));
  }
}, step.delay);
```

---

### 2. useEventSequencer.ts - Line 172: Incorrect event completion timeout
**Severity:** MEDIUM - May complete events too early or too late
**Issue:**
```typescript
const completeTimer = setTimeout(() => {
  // ...
}, sequence.displayDuration + 1000);
```

**Problem:** Only considers `displayDuration` but not the actual last step's delay. If the last step has `delay: 4000ms`, this should wait for that, not just `displayDuration + 1000ms`.

**Solution:**
```typescript
// Find the maximum delay from all steps
const maxStepDelay = Math.max(...sequence.steps.map(s => s.delay), 0);
const completeTimer = setTimeout(() => {
  // ...
}, maxStepDelay + 500); // 500ms buffer after last step
```

---

### 3. useStadiumSocket.ts - Line 120: Callbacks dependency causes infinite re-renders
**Severity:** HIGH - Can cause performance issues
**Issue:**
```typescript
}, [gameId, userId, callbacks]);
```

**Problem:** If `callbacks` object reference changes on every render, this effect will re-subscribe to WebSocket repeatedly, causing memory leaks and connection churn.

**Solution:**
```typescript
}, [gameId, userId]);
// Remove callbacks from dependencies, they're stable references
```

---

### 4. StadiumShowcaseScreen.tsx - Line 106: Event type mapping too simplistic
**Severity:** MEDIUM - Events may not be recognized
**Issue:**
```typescript
const eventTypeKey = eventType.replace(/ /g, '_').toUpperCase();
```

**Problem:** Backend sends `payload.event` in different formats:
- "HOME_RUN" → "HOME_RUN" ✅
- "Home Run" → "HOME_RUN" ✅
- "HIT_1B" → "HIT_1B" ✅
- "1B" → "1B" (no match for "HIT_1B") ❌
- "WALK" → "WALK" (no match in EVENT_SEQUENCES) ❌

**Solution:**
Create a mapping function:
```typescript
const EVENT_TYPE_MAP: Record<string, keyof typeof EVENT_SEQUENCES> = {
  'HOME_RUN': 'HOME_RUN',
  'HOME RUN': 'HOME_RUN',
  'STRIKEOUT': 'STRIKEOUT',
  'K': 'STRIKEOUT',
  'HIT_1B': 'HIT_1B',
  '1B': 'HIT_1B',
  'HIT_2B': 'HIT_2B',
  '2B': 'HIT_2B',
  'HIT_3B': 'HIT_3B',
  '3B': 'HIT_3B',
  'BALL': 'BALL',
  'STRIKE': 'STRIKE',
  'OUT_FLYBALL': 'OUT_FLYBALL',
  'FLY': 'OUT_FLYBALL',
  'OUT_GROUNDBALL': 'OUT_GROUNDBALL',
  'GROUND': 'OUT_GROUNDBALL',
  'WALK': 'BALL', // Temporary: needs proper EVENT_SEQUENCES entry
  'HIT': 'HIT_1B', // Default
};

const eventTypeKey = EVENT_TYPE_MAP[eventType] || 'HIT_1B'; // Safe fallback
```

---

### 5. useEventSequencer.ts - Timer cleanup may not be complete
**Severity:** MEDIUM - Potential memory leaks
**Issue:**
```typescript
return () => {
  // Cleanup: cancelar todos los timers si el efecto se desmonta
  Array.from(timersRef.current.keys()).forEach(key => {
    const timer = timersRef.current.get(key);
    if (timer) clearTimeout(timer);
  });
  timersRef.current.clear();
  processingRef.current = false;
};
```

**Problem:** Cleanup runs every render. If a new event is enqueued before the last effect completes, it may clear the wrong timers.

**Solution:**
```typescript
return () => {
  // Only clear timers for this specific event
  Array.from(timersRef.current.keys()).forEach(key => {
    if (key.startsWith(event.id)) {
      const timer = timersRef.current.get(key);
      if (timer) clearTimeout(timer);
      timersRef.current.delete(key);
    }
  });
};
```

---

## Warnings (Non-Critical)

### W1. StadiumShowcaseScreen.tsx: Missing error boundary
Even though PlayResultOverlay shouldn't throw, wrapping it in an ErrorBoundary would be safer.

### W2. useEventSequencer.ts: No maximum queue size
If events are queued faster than they're processed, the queue could grow infinitely.

**Solution:**
```typescript
const MAX_QUEUE_SIZE = 50;
if (queue.length >= MAX_QUEUE_SIZE) {
  console.warn('⚠️  Event queue full, dropping oldest event');
  setQueue(prev => prev.slice(1));
}
```

---

## Summary

| Issue | Severity | Impact | Easy Fix |
|-------|----------|--------|----------|
| Async setTimeout | HIGH | Event processing breaks | Yes |
| Wrong timeout calc | MEDIUM | Timing issues | Yes |
| Callbacks dependency | HIGH | Infinite re-renders | Yes |
| Event type mapping | MEDIUM | Events not recognized | Yes |
| Timer cleanup | MEDIUM | Memory leaks | Yes |
| No queue limit | LOW | Memory issues | Yes |

**Total:** 6 issues to fix (5 fixes needed before testing)
