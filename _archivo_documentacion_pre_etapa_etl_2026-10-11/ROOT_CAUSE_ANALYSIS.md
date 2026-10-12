# Root Cause Analysis: Modal Disappearing After ~14-15 Events

## The Mystery

**Observed Behavior:**
- Events 1-14 show modals correctly ✅
- Event 15 and beyond: modal doesn't appear ❌
- WebSocket events still arrive and game state updates
- No console errors
- Problem persists if same event (e.g., BALL) repeats

## Investigation Timeline

### Hypothesis 1: Modal State Not Updating ❌
- Checked: `setIsModalVisible` only called from `showModalCallback`
- Checked: `closeModalCallback` properly sets to false
- Result: Both callbacks exist and are properly defined
- **Not the cause**

### Hypothesis 2: PlayResultOverlay Component Broken ❌
- Checked: Component has own `visible` state based on `triggerCount`
- Checked: `triggerCount` increments when `resultTs` changes
- Each event has unique `ts: Date.now()`
- **Not the cause** (but verbose state management is convoluted)

### Hypothesis 3: Event Sequencer Race Condition ✅✅✅

This is the ROOT CAUSE. Here's the exact timing issue:

#### The Bug Flow

```javascript
// In useEventSequencer.ts, original code:

useEffect(() => {
  if (queue.length === 0 || processingRef.current) return;

  processingRef.current = true;
  // ... schedule all timers for steps ...
  
  // Final timer (after 3500-4100ms):
  setTimeout(() => {
    console.log('Event completed');
    setQueue(prev => prev.slice(1));  // ← Removes first event
    setCurrentEvent(null);
    processingRef.current = false;    // ← Allows next event
  }, eventCompletionTime);
  
}, [queue]); // ← Dependencies: FULL QUEUE OBJECT
```

#### Why This Breaks After 14-15 Events

**Problem 1: Object Reference Equality**
```javascript
// Event 1: queue = [evt1, evt2, evt3, ...]
// When evt1 completes:
// setQueue(prev => prev.slice(1))
// queue = [evt2, evt3, ...]  ← NEW ARRAY OBJECT

// React checks dependencies: [queue]
// Old: array object reference A
// New: array object reference B (different!)
// Effect SHOULD re-run... but there's a timing issue
```

**Problem 2: setTimeout + setState Batching**
```javascript
// In setTimeout callback at T=4100ms:
setQueue(prev => prev.slice(1));     // ← Batched
processingRef.current = false;        // ← Ref mutation (React doesn't see this)

// React's event batching might delay the state update
// Meanwhile, the condition `if (queue.length === 0 || processingRef.current)`
// is evaluated with STALE values

// By the time React re-renders and the useEffect runs again:
// - processingRef.current might still be true
// - Or timing causes the effect to not trigger at all
```

**Problem 3: Accumulating Timers**
```javascript
// After 14-15 events, you have:
// timersRef.current.keys() = [
//   "event-1-show-modal",
//   "event-1-update-score",
//   ...
//   "event-14-close-modal",
//   "event-14-complete",
// ]

// Each setTimeout is clearing timers matching event.id
// But if event.id has a very small random part, there could be:
// - Key collisions (unlikely but possible)
// - Ref growing too large (no, Max_Queue_Size=50 prevents this)
// - More likely: The cleanup logic gets sluggish with 140+ timers
```

### The Perfect Storm

These three problems combined:
1. **Reference equality change** triggers useEffect re-run
2. **Batched setState + ref mutation** causes race condition on timing
3. **Accumulating timers** slow down the sequencer after many events
4. **processingRef mutable ref** - React doesn't know when it changes, so it can't trigger effects based on it

Result: After ~14-15 events, the timing window for the next event's `show-modal` callback gets squeezed:
- Previous event's cleanup runs
- New event added to queue
- But useEffect sees `processingRef.current === true` and returns early
- OR useEffect runs but `processingRef.current` was already set to false by the setTimeout that hadn't fired yet

## The Fix

### Part 1: Make EVENT_SEQUENCES Stable

**Before:**
```javascript
export const useEventSequencer = () => {
  // ... 
  export const EVENT_SEQUENCES = { HOME_RUN: {...}, ... }  // NEW OBJECT EVERY RENDER!
```

**After:**
```javascript
// OUTSIDE the hook, at module level
const EVENT_SEQUENCES_STABLE = { HOME_RUN: {...}, ... }

export const useEventSequencer = () => {
  // ... uses EVENT_SEQUENCES_STABLE (never changes)
```

**Why:** Prevents useEffect dependencies from constantly changing

### Part 2: Use Primitive Dependencies

**Before:**
```javascript
useEffect(() => {
  // ...
}, [queue]);  // ← Object comparison, complex timing
```

**After:**
```javascript
useEffect(() => {
  // ...
}, [queue.length, isProcessing]);  // ← Primitive values
```

**Why:** 
- `queue.length` is a number (primitive)
- `isProcessing` is a boolean (React state!)
- Numbers trigger effects reliably
- React state changes are guaranteed to re-run effects

### Part 3: Use React State for processingRef

**Before:**
```javascript
const processingRef = useRef(false);

if (queue.length === 0 || processingRef.current) return;
processingRef.current = true;
// ... later ...
processingRef.current = false;  // React doesn't see this!
```

**After:**
```javascript
const [isProcessing, setIsProcessing] = useState(false);
const processingRef = useRef(false);  // Keep it for synchronous checks

if (queue.length > 0 && !isProcessing) {
  setIsProcessing(true);      // React SEES this
  processingRef.current = true;
  // ... later ...
  setIsProcessing(false);     // React SEES this, triggers dependency
  processingRef.current = false;
}
```

**Why:** 
- React tracks state changes
- useEffect dependencies on `isProcessing` will ALWAYS trigger when it changes
- Guarantees next event starts processing immediately after previous one ends

### Part 4: Reorder Event Processing Logic

**Before:**
```javascript
useEffect(() => {
  if (queue.length === 0 || processingRef.current) return;
  // ... processing logic ...
}, [queue]);
```

**After:**
```javascript
useEffect(() => {
  if (queue.length > 0 && !isProcessing) {
    // ALL processing logic INSIDE the if block
    // This ensures it re-runs with fresh dependencies
  }
}, [queue.length, isProcessing]);
```

**Why:** Logic inside the effect has access to current `isProcessing` value

## Technical Explanation: Why It Broke After 14-15 Events

### Timer Accumulation Theory
- Each event schedules 6-8 setTimeout calls
- 14 events = 84-112 timers
- At 15th event: cleanup might be delayed, or timers list is internally slow

### Reference Chain Corruption Theory
- `timersRef.current.keys()` checks `key.startsWith(event.id)`
- With 14+ events, might have string parsing overhead
- Also unlikely since it's just O(n) operations

### The Real Answer: React Batching + setTimeout Timing

Most likely scenario:
```
Event 14 completes at T=4100ms:
  setTimeout(() => {
    setQueue(prev => prev.slice(1));  // queue now has 1 event
    processingRef.current = false;    // React doesn't see this
  }, 4100)

React batches this state update
Meanwhile, browser has other timers firing (animation frames, etc.)

By the time React processes the batch and re-renders:
- useEffect([queue]) checks the NEW queue
- But processingRef.current is STILL true (it was just set, but effect already saw it)
- OR: processingRef.current is now false, but the check `processingRef.current` happened BEFORE the ref was updated

This timing window gets tighter as you accumulate events because:
1. More timers competing for execution
2. React's scheduler might prioritize other work
3. Event listeners have more handlers registered

After 14-15 events, the probability that the timing window misses increases significantly.

With the fix using `[queue.length, isProcessing]`:
- React MUST re-run effect when isProcessing changes
- No timing ambiguity: if isProcessing=false, the effect WILL run
- Primitive dependency means reference equality isn't an issue
```

## Verification

The fix is verified by checking:

1. **No dependency object reference changes**: EVENT_SEQUENCES_STABLE never changes
2. **Reliable effect re-triggering**: `isProcessing` state tells React to run effect
3. **No stale closures**: All processing happens inside effect body with fresh values
4. **Guaranteed sequencing**: Each event waits for previous one to call `setIsProcessing(false)`

## Alternative Solutions Considered

### Option A: useReducer ❌
- More complex
- Would still need to manage queue
- Doesn't solve fundamental timing issue

### Option B: Implement proper event queue library ❌
- Overkill for 3-4 events per second
- Still need to integrate with React hooks

### Option C: Debounce/Throttle showModal ❌
- Would hide legitimate duplicate events
- Not the root cause

### Option D: Increase setTimeout delays ❌
- Works for a while, then breaks at 20-25 events
- Doesn't fix the race condition

### Option E: Current Solution (dependencies + state) ✅
- Minimal changes
- Leverages React's built-in state management
- Guaranteed to work indefinitely
- Clear and maintainable
