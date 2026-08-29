# Quick Reference - Event Sequencing Fix

## One-Sentence Summary
Fixed `ReferenceError: setGameState is not defined` by moving state updates back to the WebSocket hook where they belong, instead of trying to call them from the Event Sequencer callback.

## The Bug
```javascript
// ❌ WRONG: setGameState doesn't exist in this scope
useEffect(() => {
  onStep('show-modal', (payload) => {
    setGameState(parseStateData(payload));  // ERROR!
  });
});
```

## The Fix
```javascript
// ✅ RIGHT: Update state inside the hook
case 'PLAY_RESOLVED':
  setGameState(parseStateData(payload));  // Inside useStadiumSocket
  callbacks?.onPlayResolved?.(payload);   // Pass to sequencer
  break;
```

## Why It Works

| Aspect | Wrong Approach | Correct Approach |
|--------|---|---|
| **Where to update state** | In the callback | In the hook |
| **Who owns gameState** | Component | Hook |
| **Event Sequencer's job** | Control state updates | Control callback timing |
| **CSS z-index's job** | Doesn't matter | Determines visual priority |

## Three Types of State

```
🪝 Hook State (useStadiumSocket)
   └─ gameState ← Updates when WebSocket message arrives
   └─ hasPitched
   └─ isConnected

📦 Component State (StadiumShowcaseScreen)
   └─ lastResult ← Set by show-modal callback
   └─ isAwaitingResult
   └─ pitcherCard
   └─ etc.

⏱️ Sequencer State (useEventSequencer)
   └─ Controls CALLBACK TIMING (not state updates)
   └─ 0ms: show-modal
   └─ 3100ms: update-score
```

## Data Flow (Simplified)

```
WebSocket → Hook Updates gameState → Component Gets New Props → Callbacks Trigger → UI Updates
```

## Console Logs to Expect

✅ Good:
```
🔵 [FRONTEND] PLAY_RESOLVED received
📤 [HANDLER] Enqueuing PLAY_RESOLVED event
⚙️  [EVENT SEQUENCER] Processing event
✅ [STEP] show-modal - Setting PlayResultOverlay
```

❌ Bad:
```
❌ [STEP] Error in show-modal: ReferenceError: setGameState is not defined
```

## Files Changed

### File 1: `frontend/src/hooks/useStadiumSocket.ts`
```diff
case 'PLAY_RESOLVED':
  payload = data as PlayResolvedPayload;
+ setGameState(parseStateData(payload));  // ← RESTORED
  callbacks?.onPlayResolved?.(payload);
  break;
```

### File 2: `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`
```diff
onStep('show-modal', (payload) => {
  setLastResult({...});
- setGameState(parseStateData(payload));  // ← REMOVED
  setIsAwaitingResult(true);
});
```

## Rebuild & Test

```bash
# 1. Restart container (rebuilds code)
docker-compose restart frontend

# 2. Wait 60 seconds

# 3. Hard refresh browser
Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

# 4. Play a game event

# 5. Check console for logs (above)
```

## Verification

| Check | Status |
|-------|--------|
| ✅ Modal appears when event happens | Should be YES |
| ✅ Console shows clean [STEP] logs | Should be YES |
| ❌ `setGameState is not defined` error | Should be NO |
| ✅ Scorecard updates after modal | Should be YES |

## Key Insight

**React hooks manage their own state.** You can't call `setGameState` from outside the hook that created it. The hook can update its own state when WebSocket messages arrive, and the component receives that updated state via props.

The Event Sequencer controls **when callbacks run**, not **when state updates**. State updates happen immediately when data arrives. Callbacks run on a schedule for UI effects.

## Related Documents

- `IMMEDIATE_ACTIONS.md` - Step-by-step to test
- `ROOT_CAUSE_ANALYSIS.md` - Deep dive into what went wrong
- `FINAL_FIX_SUMMARY.md` - Complete explanation
- `TESTING_SEQUENCING_FIX.md` - Comprehensive testing guide
