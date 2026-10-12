# WebSocket Gameplay Sequencing - Complete Fixes

## Problem Summary
1. **Duplicate State Updates**: gameState updates immediately from WebSocket, but then callbacks execute sequenced timings
2. **Duplicate Stats Storage**: batter_stats and pitcher_strikeouts stored in both `gameState` and `gameStats`
3. **Multiple Pitcher/Batter Card Sources**: 5 different effects updating `pitcherCard` and `batterCard`
4. **Inconsistent Component Freezing**: Some components use frozen `displayedGameState`, others use live `gameState`
5. **Missing Event Documentation**: No clear step-by-step comments on how events flow

## Solution Strategy

### Phase 1: Document the Flow (Do First)
Add detailed comments in StadiumShowcaseScreen explaining:
- How WebSocket payload arrives
- When freeze/unfreeze happens
- Which components use which state
- Where each update originates

### Phase 2: Remove Duplicate Storage
- Delete `gameStats` state
- Use `gameState.batter_stats` and `gameState.pitcher_strikeouts` directly
- Remove copying effect (lines 501-526)

### Phase 3: Consolidate Card Updates
- Remove all 5 sources of pitcher/batter card updates
- Use ONLY `gameState.active_pitcher` and `gameState.active_batter`
- Single effect that mirrors to local state when gameState updates
- Remove WebSocket PITCHER_CHANGED manual handler

### Phase 4: All Components Use displayedGameState
- Find every component receiving gameState
- Replace with displayedGameState
- Verify conditional logic still works (gameState for conditions is OK)

### Phase 5: Clean Up Logs
- Remove parseStateData logs (lines 63-73)
- Keep only critical error logs
- Remove debug timestamps
- Remove unused console.logs

## Implementation Order

### 1. StadiumShowcaseScreen.tsx Changes

**DELETE THESE:**
- Lines 501-526: `gameStats` copy effect
- Lines 731-788: Pitcher card 5-source effect → replace with 1-source
- Lines 791-829: Batter card 2-source effect → replace with 1-source  
- Lines 937-964: Pitcher change effect
- Unused `strikeoutAnimationTrigger` state (line 97)
- Unused `pitcherChanged` state (line 106)

**KEEP THESE:**
- `gameState` (from WebSocket)
- `isModalVisible` + `deferredGameState` (freeze/unfreeze)
- `displayedGameState` (computed)
- `lastResult` (for modal timing)
- All event sequencer related code (correct)

**ADD THESE:**
- Documentation comments explaining flow
- Single effect for pitcher card (reads gameState.active_pitcher)
- Single effect for batter card (reads gameState.active_batter)
- Simplify stat accessors: `gameState.batter_stats` instead of `gameStats.batters`

### 2. Component Props Changes

**All display components should pass displayedGameState or fields from it:**
```typescript
// BEFORE (Mixed):
<Scoreboard gameState={gameState} inningRuns={displayedGameState?.inning_runs} />

// AFTER (Consistent):
<Scoreboard gameState={displayedGameState} inningRuns={displayedGameState?.inning_runs} />
```

Components affected:
- Scoreboard
- CentralField / PitchZoneGrid
- GameStatsPanel (both instances)
- PitcherStaminaBar
- InningTransitionModal
- PlayResultOverlay (keep as is - handles its own timing)

### 3. Logging Cleanup

**REMOVE:**
```typescript
console.log('⭐ [PARSE_STATE_DATA]...');  // Lines 63-73 in useStadiumSocket.ts
console.log('🎲 [STADIUM SHOWCASE]...');  // Debug logs
console.log('📊 [STAMINA DATA]...');     // Debug logs
console.log('✅ [SO COUNTER]...');       // Debug logs
```

**KEEP:**
```typescript
console.log('[WS] Conectado...');         // Connection status
console.log('[WS] Error...');             // Errors
console.log('❌ [FRONTEND] Error...');    // Request errors
console.log('🧊 [FREEZE]...');            // Modal freeze/unfreeze (critical for testing)
console.log('🔓 [MODAL CLOSE]...');       // Modal unfreeze (critical for testing)
```

## Event Flow Diagram (To Add as Comment)

```
┌─────────────────────────────────────────────────────────────────────┐
│ EVENT SEQUENCE - HOW A PITCH RESOLVES                               │
└─────────────────────────────────────────────────────────────────────┘

T+0ms: User clicks "ENVIAR" or swings
  └─ if PITCHER: sendPitch(zone, pitchType)
  └─ if BATTER: sendSwing(swingType, ...)
  └─ POST /api/v1/games/{gameId}/pitch

T+X ms: Backend processes (100-500ms)
  └─ Determines outcome (HOME_RUN, STRIKEOUT, HIT_1B, etc)
  └─ Updates database state
  └─ Sends PLAY_RESOLVED via WebSocket with new game state

T+X+Y ms: Frontend WebSocket Receives PLAY_RESOLVED
  ├─ parseStateData(payload) → GameStateWS object
  ├─ setGameState(gameState)  [IMMEDIATE - all data updated behind scenes]
  └─ callbacks.onPlayResolved(payload) [QUEUES for sequencing]

T+X+Y+0ms: Event Sequencer Processes
  ├─ Enqueues event with type and payload
  └─ Schedules 'show-modal' step with delay: 0ms

T+X+Y+0ms: 'show-modal' Step Executes
  ├─ setIsModalVisible(true)        [Freeze gameState]
  ├─ setDeferredGameState(gameState) [Save snapshot]
  └─ setLastResult({text, event, ts}) [Show overlay]

T+X+Y+1000ms: PlayResultOverlay Shows (after delayMs)
  ├─ Displays overlay with animation
  └─ Sound plays

T+X+Y+1000ms to T+X+Y+4500ms: User sees overlay
  ├─ displayedGameState = deferredGameState (FROZEN)
  ├─ WebSocket continues updating gameState (background)
  └─ Components render frozen values (no visual change)

T+X+Y+4500ms: Overlay Hides (after duration expires)
  ├─ PlayResultOverlay hidden
  ├─ lastResult cleared
  └─ setIsModalVisible(false) [Unfreeze]

T+X+Y+4500ms: Unfreeze Effect Triggers
  ├─ displayedGameState = gameState (LIVE)
  └─ Components re-render with background updates

T+X+Y+4600ms: Components Visually Update
  ├─ Scoreboard shows new score
  ├─ GameStatsPanel updates stats
  ├─ PitcherStaminaBar shows new pitch count
  ├─ Runners update
  └─ User sees smooth sequence: Modal → Freeze → Unfreeze → Update
```

## Testing After Fixes

1. **Compile Check**
   ```bash
   npm run build
   ```

2. **Visual Test: Single Pitch Sequence**
   - Start game
   - Throw pitch
   - Observe modal appears (freeze)
   - Wait for modal to disappear (should be 3-5 seconds)
   - Observe UI updates all at once (scores, stats, runners)

3. **Console Logs**
   - Should see: `🧊 [FREEZE]` when modal appears
   - Should see: `🔓 [MODAL CLOSE]` when modal closes
   - No stale debug logs

4. **Multiple Pitches**
   - Throw 2-3 pitches rapidly
   - Verify each one freezes independently
   - Scores update correctly after each modal

5. **Stats Accuracy**
   - Check batter AB-H stats update correctly
   - Check pitcher K count updates correctly
   - No duplicate or stale stats

## Files to Modify

1. `frontend/src/hooks/useStadiumSocket.ts` - Clean up logs
2. `frontend/src/components/stadium/StadiumShowcaseScreen.tsx` - Main fixes
3. `frontend/src/components/stadium/PlayResultOverlay.tsx` - Verify modal timing (if needed)

## Files NOT to Touch

- GameOverModal
- InningTransitionModal
- GameIntroModal
- Scoreboard
- GameStatsPanel
- PitcherStaminaBar
- PlayerCard
- All others (just update props)

These components are display-only and don't need internal changes, just updated props.
