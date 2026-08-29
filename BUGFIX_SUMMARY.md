# Modal Disappearing Bug - Root Cause & Fixes Applied

## Problem Summary
Modal was disappearing after 14-15 events or when the same event recurred multiple times.

## Root Causes Identified

### 1. **EVENT_SEQUENCES Re-definition on Each Render**
- `EVENT_SEQUENCES` was defined inside the component, creating a new object reference every render
- This caused `useEffect` dependencies to constantly change, re-triggering and canceling timers prematurely
- **Fix**: Moved to module-level as `EVENT_SEQUENCES_STABLE` constant

### 2. **useEffect Dependency Race Condition**
- Original deps: `[queue]` - compared entire queue object by reference
- When `setQueue(prev => prev.slice(1))` executed, it created a new array
- But `processingRef.current = false` was happening in the same setTimeout, causing timing issues
- Next event wouldn't trigger if React batched setState calls
- **Fix**: Changed deps to `[queue.length, isProcessing]` - primitive values that trigger properly

### 3. **No Visibility into When Events Process**
- Only relying on `processingRef` (mutable ref) meant React didn't know when processing completed
- `setIsProcessing(false)` now properly triggers the next event's processing
- **Fix**: Added `isProcessing` state alongside the ref for React to track

### 4. **Stale Callbacks Not Triggering**
- Callbacks weren't being called because processingRef check wasn't reflecting React's state
- **Fix**: Now checking `!isProcessing` which properly blocks concurrent processing

## Files Modified

### `frontend/src/hooks/useEventSequencer.ts`
- Moved `EVENT_SEQUENCES` → `EVENT_SEQUENCES_STABLE` (module-level, static)
- Export `EVENT_SEQUENCES = EVENT_SEQUENCES_STABLE` for backward compatibility
- Changed `useEffect` deps from `[queue]` to `[queue.length, isProcessing]`
- Added `setIsProcessing(true)` at start and `setIsProcessing(false)` at end of event processing
- Added logging: `📌 [REGISTER STEP]` with callback count
- Conditional `if (queue.length > 0 && !isProcessing)` ensures one event at a time

### `frontend/src/hooks/useEventSequencerCallbacks.ts`
- Enhanced logging in `showModalCallback`:
  ```
  🎬 [SHOW-MODAL] Event: <event>
  → Setting isModalVisible to TRUE
  → Setting modalEventData: {...}
  ```
- Enhanced logging in `closeModalCallback`:
  ```
  🚪 [CLOSE-MODAL] Closing modal
  → Setting isModalVisible to FALSE
  → Setting deferredGameState to NULL
  ```

### `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`
- Added monitoring useEffect:
  ```typescript
  useEffect(() => {
    console.log('📊 [STADIUM] isModalVisible STATE CHANGED:', {
      isModalVisible,
      modalEventData: modalEventData?.event,
      deferredGameState: deferredGameState?.currentInning,
    });
  }, [isModalVisible, modalEventData, deferredGameState]);
  ```

## Expected Behavior After Fix

### Event Processing Flow
1. WebSocket sends event → `enqueueEvent()` adds to queue
2. `useEffect([queue.length])` detects new event
3. `setIsProcessing(true)` → schedules all step timers
4. Each step timer executes its callback at precise delay
5. Final timer: `setIsProcessing(false)` + `setQueue(prev => prev.slice(1))`
6. `useEffect([isProcessing])` detects false → starts next event

### Console Logs to Watch
```
⚙️  [EVENT SEQUENCER] Processing event: HOME_RUN
  📍 [STEP] show-modal (delay: 0ms) - executing callback
    🎬 [SHOW-MODAL] Event: HOME_RUN
    → Setting isModalVisible to TRUE
    → Setting modalEventData: {text: "...", event: "HOME_RUN"}
    📊 [STADIUM] isModalVisible STATE CHANGED: true

  📍 [STEP] update-score (delay: 3600ms)
  📍 [STEP] close-modal (delay: 4100ms)
    🚪 [CLOSE-MODAL] Closing modal
    → Setting isModalVisible to FALSE
    📊 [STADIUM] isModalVisible STATE CHANGED: false

✅ [EVENT SEQUENCER] Event completed: HOME_RUN

⚙️  [EVENT SEQUENCER] Processing event: BALL (next event)
```

## Testing Instructions

1. Run Docker container
2. Play a game and trigger 20+ events (BALLs, STRIKEs, HOMERUNs)
3. Watch browser console for patterns:
   - Each event should have `🎬 [SHOW-MODAL]` and `🚪 [CLOSE-MODAL]`
   - `📊 [STADIUM] isModalVisible STATE CHANGED` should toggle true→false for each event
   - No gaps between events (next event's `⚙️ [EVENT SEQUENCER] Processing` should follow previous event's ✅)

4. If modal still doesn't appear:
   - Check if show-modal callback is executing (look for 🎬 log)
   - Check if `isModalVisible` state is actually changing (look for 📊 log)
   - Check console for TypeError or missing callback warnings

## Backup Plan if Still Broken
If modal still disappears, the issue might be:
- PlayResultOverlay component has its own buggy useEffect
- Modal is being rendered but styled off-screen or with opacity 0
- WebSocket event normalization is failing for certain events

Next step: Add breakpoint in PlayResultOverlay render to confirm it's being called
