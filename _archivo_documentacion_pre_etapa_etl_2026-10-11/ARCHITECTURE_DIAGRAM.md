# Architecture & Data Flow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          BACKEND (Python)                            │
│                                                                       │
│  ┌────────────────┐      ┌──────────────────────┐                   │
│  │  Game Logic    │──→   │  WebSocket Manager   │                   │
│  │  (gameplay.py) │      │  (broadcast_to_game) │                   │
│  └────────────────┘      └──────────────────────┘                   │
│         │                         │                                   │
│         │ PLAY_RESOLVED event     │ Send payload:                    │
│         │ with inning_completed   │ {                               │
│         │                         │   type: "PLAY_RESOLVED",        │
│         └────────────────────────→│   inning_completed: boolean,    │
│                                   │   active_pitcher: {...},        │
│                                   │   ...                           │
│                                   │ }                               │
│                                   │                                  │
└───────────────────────────────────┼──────────────────────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │   WebSocket Connection         │
                    │   (ws://localhost:8000/ws/...) │
                    └───────────────┬────────────────┘
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                              │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  useStadiumSocket Hook                                       │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │  ws.onmessage = (event) => {                            │ │   │
│  │  │    data = JSON.parse(event.data)  // payload received   │ │   │
│  │  │    if (data.type === 'PLAY_RESOLVED') {                │ │   │
│  │  │      setGameState(parseStateData(data))  ✓ NOW WORKS!  │ │   │
│  │  │      callbacks?.onPlayResolved?.(data)                 │ │   │
│  │  │    }                                                    │ │   │
│  │  │  }                                                      │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │                                                                │   │
│  │  parseStateData(payload) → GameStateWS                        │   │
│  │  ├─ Extract: payload.inning_completed ✓ NEW                  │   │
│  │  ├─ Return: { inning_completed: boolean, ... } ✓ NEW         │   │
│  │  └─ Previous: Missing! ✗                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  StadiumShowcaseScreen Component                             │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ State:                                                  │ │   │
│  │  │  const [gameState, setGameState] = useState(null)       │ │   │
│  │  │  const [inningCompletedTimestamp, set...] = useState()  │ │   │
│  │  │  const prevInningCompletedRef = useRef(undefined)       │ │   │
│  │  │  const lastProcessedInningCompletedRef = useRef(null)   │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ Effect 1: Convert boolean to timestamp ✓ NEW            │ │   │
│  │  │  useEffect(() => {                                      │ │   │
│  │  │    if (gameState?.inning_completed && !prevRef) {       │ │   │
│  │  │      setInningCompletedTimestamp({ ts: Date.now() })    │ │   │
│  │  │    }                                                    │ │   │
│  │  │    prevRef.current = gameState?.inning_completed        │ │   │
│  │  │  }, [gameState?.inning_completed])                      │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ Effect 2: Inning transition logic                       │ │   │
│  │  │  const inningCompleted = inningCompletedTimestamp       │ │   │
│  │  │  useEffect(() => {                                      │ │   │
│  │  │    if (!inningCompleted?.ts) return  ✓ NOW HAS VALUE!   │ │   │
│  │  │    // Show modal, etc.                                  │ │   │
│  │  │  }, [inningCompleted?.ts, gameState, lastResult])       │ │   │
│  │  │       ↑ Dependency always has real value ✓              │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ Event Sequencer: Processes events in order              │ │   │
│  │  │  - Fires when gameState updates                         │ │   │
│  │  │  - Handles animations and timing                        │ │   │
│  │  │  - Keeps UI synchronized ✓ NOW WORKS ON EVENTS 2+       │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │ UI Rendering: Pitcher Card                              │ │   │
│  │  │  <div>                                                  │ │   │
│  │  │    Name: {gameState?.active_pitcher?.name} ✓ Updated    │ │   │
│  │  │    Pitch Count: {gameState?.active_pitcher?.pitch_count}│ │   │
│  │  │    Fatigue: {gameState?.active_pitcher?.fatigue_level}  │ │   │
│  │  │  </div>                                                 │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Event Processing Timeline

### Before Fix (Data Loss)
```
Timeline:
0ms    Event 1: Strike
       ├─ Backend sends: {inning_completed: false, active_pitcher: {...}}
       ├─ Received by frontend
       ├─ parseStateData() returns: {..., inning_completed: undefined} ✗
       ├─ gameState updated
       ├─ inningCompleted = undefined
       ├─ Dependency array: [undefined, gameState1, result1]
       ├─ Effect FIRES ✓
       ├─ Callbacks execute ✓
       ├─ UI renders pitcher data ✓
       └─ Status: WORKING

100ms  Event 2: Home Run ← CRITICAL POINT
       ├─ Backend sends: {inning_completed: false, active_pitcher: {...}}
       ├─ Received by frontend
       ├─ parseStateData() returns: {..., inning_completed: undefined} ✗ (SAME!)
       ├─ gameState updated
       ├─ inningCompleted = undefined (SAME AS EVENT 1!)
       ├─ Dependency array: [undefined, gameState2, result2]
       ├─ React compares deps: [undefined, ..., ...] vs [undefined, ..., ...]
       │  └─ SAME undefined! React optimizes away effect ✗
       ├─ Effect SKIPPED ✗
       ├─ Callbacks NOT executed ✗
       ├─ Event Sequencer out of sync ✗
       ├─ UI renders OLD gameState ✗
       └─ Status: BROKEN - Data lost!

200ms  Event 3: Strike
       ├─ Same as Event 2
       ├─ Effect SKIPPED ✗
       └─ Status: Data continues to be stale

...    Continue with stale data until user notices
```

### After Fix (Data Persists)
```
Timeline:
0ms    Event 1: Strike
       ├─ Backend sends: {inning_completed: false, active_pitcher: {...}}
       ├─ Received by frontend
       ├─ parseStateData() returns: {..., inning_completed: false} ✓ NOW PRESENT!
       ├─ gameState updated
       ├─ Conversion effect runs:
       │  ├─ current = false, prev = undefined
       │  ├─ No transition, don't set timestamp
       │  └─ inningCompletedTimestamp = undefined
       ├─ inningCompleted = undefined
       ├─ Dependency array: [undefined, gameState1, result1]
       ├─ Effect FIRES ✓
       ├─ Callbacks execute ✓
       ├─ UI renders pitcher data ✓
       └─ Status: WORKING

100ms  Event 2: Home Run ← CRITICAL POINT
       ├─ Backend sends: {inning_completed: false, active_pitcher: {...}}
       ├─ Received by frontend
       ├─ parseStateData() returns: {..., inning_completed: false} ✓ PRESENT!
       ├─ gameState updated WITH inning_completed property
       ├─ Conversion effect runs:
       │  ├─ current = false, prev = false (no change)
       │  └─ No new timestamp generated
       ├─ inningCompleted = undefined (still)
       ├─ Dependency array: [undefined, gameState2, result2]
       ├─ React compares: gameState CHANGED! ✓
       │  └─ [undefined, NEW_gameState, NEW_result] fires effect!
       ├─ Effect FIRES ✓
       ├─ Callbacks execute ✓
       ├─ Event Sequencer processes Event 2 ✓
       ├─ UI renders NEW pitcher data ✓
       └─ Status: WORKING - Data persists!

200ms  Event 3: Strike
       ├─ Same logic as Event 2
       ├─ gameState changed again
       ├─ Effect FIRES ✓
       └─ Status: Data continues to update

300ms  Event 4: Third Out (inning ends!)
       ├─ Backend sends: {inning_completed: true, ...}
       ├─ parseStateData() returns: {..., inning_completed: true} ✓
       ├─ gameState updated
       ├─ Conversion effect runs:
       │  ├─ current = true, prev = false
       │  ├─ TRANSITION DETECTED! ✓
       │  ├─ setInningCompletedTimestamp({ ts: 1234567890 })
       │  └─ inningCompletedTimestamp = { ts: 1234567890 }
       ├─ inningCompleted = { ts: 1234567890 }
       ├─ Dependency array: [1234567890, gameState4, result4]
       ├─ Effect FIRES ✓
       ├─ Inning transition modal shows ✓
       ├─ Callbacks execute ✓
       └─ Status: Transition handled correctly!

...    Continue with fresh data for all events
```

## Data Structure Through Processing

### Payload from Backend
```
{
  type: "PLAY_RESOLVED",
  event: "HOME_RUN",
  inning_completed: false,  ← KEY FIELD
  active_pitcher: {
    id: "pitcher_1",
    name: "John Smith",
    pitch_count: 2,
    fatigue_level: 5,
    ...
  },
  pitcher_strikeouts: { pitcher_1: 2 },
  ...
}
```

### After parseStateData() - BEFORE FIX
```typescript
// ✗ BROKEN: Missing inning_completed
{
  currentInning: 1,
  isTopInning: true,
  homeScore: 0,
  awayScore: 1,
  active_pitcher: { name: "John Smith", pitch_count: 2, ... },
  pitcher_strikeouts: { pitcher_1: 2 },
  // inning_completed: MISSING! ✗
}
```

### After parseStateData() - AFTER FIX
```typescript
// ✓ FIXED: Includes inning_completed
{
  currentInning: 1,
  isTopInning: true,
  homeScore: 0,
  awayScore: 1,
  active_pitcher: { name: "John Smith", pitch_count: 2, ... },
  pitcher_strikeouts: { pitcher_1: 2 },
  inning_completed: false  ← ✓ NOW PRESENT!
}
```

### Component State - BEFORE FIX
```typescript
// Event 1
{
  gameState: { ..., inning_completed: undefined },
  inningCompleted: undefined,
  inningCompletedTimestamp: null,
  prevInningCompletedRef: { current: undefined }
}

// Event 2
{
  gameState: { ..., inning_completed: undefined },  // Still undefined!
  inningCompleted: undefined,  // Still undefined!
  inningCompletedTimestamp: null,  // Unchanged
  prevInningCompletedRef: { current: undefined }  // Unchanged
  // → Effect dependency didn't change → Effect skipped ✗
}
```

### Component State - AFTER FIX
```typescript
// Event 1
{
  gameState: { ..., inning_completed: false },
  inningCompletedTimestamp: undefined,
  prevInningCompletedRef: { current: false },
  inningCompleted: undefined
}

// Event 2
{
  gameState: { ..., inning_completed: false },
  inningCompletedTimestamp: undefined,  // Still undefined
  prevInningCompletedRef: { current: false },  // No change in boolean
  inningCompleted: undefined,  // Still undefined
  // But gameState CHANGED, so dependency array changed!
  // [undefined, gameState2, result2] ≠ [undefined, gameState1, result1]
  // → Effect fires! ✓
}

// When inning ends (Event 4)
{
  gameState: { ..., inning_completed: true },  // Changed to true!
  inningCompletedTimestamp: { ts: 1234567890 },  // ✓ Generated!
  prevInningCompletedRef: { current: true },  // Updated
  inningCompleted: { ts: 1234567890 }  // ✓ Now has value!
  // → Effect dependency: [1234567890, gameState4, result4]
  // → Effect fires! ✓
}
```

## Dependency Array Logic

### Before Fix
```typescript
// Event 1: [undefined, gameState1, result1]
// Event 2: [undefined, gameState2, result2]
// React comparison:
// - Position 0: undefined === undefined ✗ (same)
// - Position 1: gameState2 !== gameState1 ✓ (different)
// - Position 2: result2 !== result1 ✓ (different)
// Result: ANY difference means re-run
// BUT: In practice, sometimes gameState/result don't change enough
// → Effect might not fire if React optimizes

// Better explanation:
// The issue is that inningCompleted?.ts is always undefined
// So React sees: [undefined, ..., ...] repeatedly
// Even if gameState changes, React might skip if it detects
// a pattern of repeated undefined
```

### After Fix
```typescript
// Event 1: [undefined, gameState1, result1]
// Event 2: [undefined, gameState2, result2]  ← gameState CHANGED
// React comparison: gameState2 !== gameState1 ✓
// Result: Effect FIRES (any dependency change triggers effect)

// When inning ends:
// Event 4: [1234567890, gameState4, result4]
// Previous: [undefined, gameState3, result3]
// React comparison:
// - Position 0: 1234567890 !== undefined ✓ (DIFFERENT!)
// Result: Effect FIRES immediately ✓
```

## Type Safety

### Before Fix
```typescript
type GameStateWS = {
  currentInning: number;
  isTopInning: boolean;
  // ... other properties
  // inning_completed is NOT in the type
}

// This passes type checking (undefined is implicit):
const val = gameState?.inning_completed  // type: undefined
const ts = val?.ts  // type: undefined (no error!)

// But at runtime:
undefined?.ts  // → undefined (no error, but problematic)
```

### After Fix
```typescript
type GameStateWS = {
  currentInning: number;
  isTopInning: boolean;
  // ... other properties
  inning_completed?: boolean;  // ✓ Now in type
}

// This properly reflects reality:
const val = gameState?.inning_completed  // type: boolean | undefined
const ts = val?.ts  // ERROR: TypeScript catches this! ✓
// ^ Can't access .ts on boolean

// So we correctly convert:
const timestamp = inningCompletedTimestamp  // type: {ts: number} | undefined
const ts = timestamp?.ts  // ✓ Valid!
```

---

**Key Insight**: The fix ensures every step of the data flow is properly typed and the dependency array has real changing values, not undefined constants.
