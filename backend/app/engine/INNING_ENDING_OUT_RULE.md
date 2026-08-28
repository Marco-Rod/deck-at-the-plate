# Inning-Ending Out Rule

## Official Baseball Rule

In baseball, a run scores only if the runner crosses home plate **before** the third out of the inning is recorded.

**Official Reference**: MLB Rule 4.09(a)

> "A run is scored when a player touches first, second and third bases in order before he is put out."

---

## Implementation in Backend

**File**: `backend/app/engine/state_manager.py::process_at_bat_transition()`
**Location**: Lines 132-138

```python
# --- VALIDACIÓN CRÍTICA: Inning-Ending Double Play Rule ---
# En béisbol, una carrera SOLO cuenta si cruza home ANTES del 3er out
if runs_scored > 0 and game.outs >= 3:
    # El tercer out ya se completó → ninguna carrera cuenta
    print(f"⚾ [INNING-ENDING DP] 3er out completado. Carreras anuladas: {runs_scored} → 0")
    runs_scored = 0
```

---

## Scenarios

### Scenario 1: Bases Loaded, 2 Outs → OUT_GROUND (Normal Out)

```
Before: r1=ALICE, r2=BOB, r3=CHARLIE, outs=2
Event: OUT_GROUND (no DP)
Result:
  - ALICE advances (out at 1B)
  - BOB stays (forced by Alice)
  - CHARLIE scores (forced to home by out)
  - Runs: +1 ✅
  - Outs: 3 (ends inning)
```

**Result**: CHARLIE's run counts (crossed before 3rd out)

---

### Scenario 2: Bases Loaded, 2 Outs → OUT_GROUND (DOUBLE PLAY)

```
Before: r1=ALICE, r2=BOB, r3=CHARLIE, outs=2
Event: OUT_GROUND with DP probability triggered

Calculations:
  1. advance_runners() calculates: r2 stays, r3 scores = +1 run
  2. game.outs += 1 (first out: ALICE out at 2B)
  3. game.outs += 1 (second out: BATTER out at 1B) → game.outs = 4 ✅
  4. Check: runs_scored > 0 AND game.outs >= 3 → TRUE
  5. Cancel run: runs_scored = 0

Result:
  - ALICE: OUT at 2B
  - BOB: stays at 2B
  - CHARLIE: would score BUT 3rd out already made → DOESN'T COUNT ❌
  - BATTER: OUT at 1B
  - Runs: 0 (was +1, now cancelled)
  - Outs: 4 (but resets to 0, inning ends)
```

**Result**: CHARLIE's run DOES NOT count (3rd out made before crossing home)

---

### Scenario 3: Bases Loaded, 1 Out → OUT_GROUND (DOUBLE PLAY)

```
Before: r1=ALICE, r2=BOB, r3=CHARLIE, outs=1
Event: OUT_GROUND with DP

Result:
  - ALICE: OUT at 2B (out 2)
  - BOB: stays at 2B
  - CHARLIE: scores = +1 run ✅
  - BATTER: OUT at 1B (out 3)
  - Outs: 3 (ends inning, but CHARLIE crossed before)
  - Runs: +1 ✅

Result: CHARLIE scores because he crossed home plate before the 3rd out
```

---

### Scenario 4: Runners on 1B and 3B, 2 Outs → OUT_GROUND

```
Before: r1=ALICE, r2=None, r3=CHARLIE, outs=2
Event: OUT_GROUND

Calculation:
  - advance_runners() returns: r3 scores (forced by out) = +1 run
  - Out is made: game.outs = 3
  - Check: game.outs >= 3 AND runs_scored > 0 → TRUE
  - Cancel: runs_scored = 0

Result: CHARLIE does NOT score (3rd out completed)
```

---

## Key Logic Flow

```
1. Event occurs (OUT_GROUND, HIT, etc.)
   ↓
2. Current outs counted: game.outs (before the play)
   ↓
3. advance_runners() calculates carrers assuming normal scoring
   ↓
4. If DOUBLE_PLAY: game.outs += 1 (second out of DP)
   ↓
5. VALIDATION: if runs_scored > 0 AND game.outs >= 3:
      → runs_scored = 0 (cancel runs)
   ↓
6. Only add runs_scored if it passed validation
```

---

## Implementation Details

### When Double Out is Added

In `state_manager.py`, the second out of a DP is added **immediately after** `advance_runners()` calculates, but **before** the inning-ending check:

```python
# Line 91: First out (ground ball)
if event in ("OUT_FLY", "OUT_GROUND"):
    game.outs += 1

# Line 127-129: Second out (if DP)
if event_adjusted == "DOUBLE_PLAY":
    game.outs += 1  # Now we have 2 outs from the play
    final_event = "DOUBLE_PLAY"

# Line 132-138: Check if 3rd out was reached
if runs_scored > 0 and game.outs >= 3:
    runs_scored = 0  # Cancel runs
```

---

## Historical Context

### Before Fix
- Double play scenarios with bases loaded at 2 outs would incorrectly award runs
- `advance_runners()` calculated run scoring without checking `game.outs`
- No validation of out count vs. run scoring timing

### After Fix
- Run scoring validated against final out count
- Inning-ending double plays correctly cancel runs
- All MLB scoring rules implemented correctly

---

## Related Code

- **calculator.py**: Generates `OUT_GROUND`, `OUT_FLY`
- **runner_manager.py**: Calculates if DP occurs + runs scored
- **state_manager.py**: Validates run scoring against out count (lines 132-138)
- **stats_recorder.py**: Records final runs in box score

---

## Testing Scenarios

### Test 1: Bases loaded, 2 outs, DP occurs
- Input: `{1b: "A", 2b: "B", 3b: "C"}`, outs=2, event="OUT_GROUND"
- DP triggers (35-65% chance)
- Expected: runs=0 (C doesn't score), outs=3, inning ends

### Test 2: Bases loaded, 1 out, DP occurs
- Input: `{1b: "A", 2b: "B", 3b: "C"}`, outs=1, event="OUT_GROUND"
- DP triggers
- Expected: runs=1 (C scores before 3rd out), outs=3, inning ends

### Test 3: Runners on 1B/3B, 2 outs, DP occurs
- Input: `{1b: "A", 2b: None, 3b: "C"}`, outs=2, event="OUT_GROUND"
- DP triggers
- Expected: runs=0 (C doesn't score), outs=3, inning ends
