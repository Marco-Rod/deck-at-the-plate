# Double Play Rules Reference

This document describes all double play scenarios in baseball and how they're implemented.

## Background

A double play occurs when **two outs are made on a single play**. The most common is the **ground ball double play** (GIDP), which happens when:
- A ground ball is hit with a runner on 1B
- The defense forces out the runner at 2B and the batter at 1B

## Implementation in Backend

**File**: `backend/app/engine/runner_manager.py::advance_runners()`
**Event**: `OUT_GROUND` with runner on 1B
**Probability**: 75% (65% if also runner on 2B)

---

## All Double Play Scenarios

### Scenario 1: Runner on 1B Only (Bases: 1B Occupied)

```
Before: r1=PLAYER_A, r2=None, r3=None
Event: OUT_GROUND
Probability: 75% → DOUBLE PLAY, 25% → Single OUT

IF DOUBLE PLAY:
  After:  r1=None, r2=None, r3=None
  Runs:   0
  Outs:   +2

Logic:
- r1 forced out at 2B
- Batter out at 1B
- No one advances
```

---

### Scenario 2: Runners on 1B and 2B (Bases: 1B & 2B Occupied) ⭐

```
Before: r1=PLAYER_A, r2=PLAYER_B, r3=None
Event: OUT_GROUND
Probability: 65% → DOUBLE PLAY, 35% → Single OUT

IF DOUBLE PLAY:
  After:  r1=None, r2=PLAYER_B, r3=None
  Runs:   0
  Outs:   +2

Logic:
- r1 forced out at 2B
- Batter out at 1B
- r2 stays at 2B (no force advance to 3B without another runner forcing)
- r3 would advance to home IF it existed (force)

NOTE: r2 does NOT advance to 3B automatically. The force is only from the
      new batter (now out at 1B) and r1 (now out at 2B). r2 was already
      forced to run, but since r1 is out, there's no force on r2 anymore.
      r2 stays at 2B.
```

---

### Scenario 3: Bases Loaded (1B, 2B, 3B Occupied) ⭐ MOST COMMON

```
Before: r1=PLAYER_A, r2=PLAYER_B, r3=PLAYER_C
Event: OUT_GROUND
Probability: 65% → DOUBLE PLAY, 35% → Single OUT

IF DOUBLE PLAY:
  After:  r1=None, r2=PLAYER_B, r3=None
  Runs:   1 (r3 scores on the force)
  Outs:   +2

Logic:
- r1 forced out at 2B
- Batter out at 1B
- r3 SCORES (forced to run by all the outs)
- r2 stays at 2B (no force to 3B after r1 is out)

IMPORTANT: r3 scores because the bases are loaded and there's a force
           at every base. When r1 is forced out at 2B, it breaks the
           force chain, but r3 has already crossed home.
```

---

### Scenario 4: Runners on 1B and 3B (Bases: 1B & 3B Occupied)

```
Before: r1=PLAYER_A, r2=None, r3=PLAYER_C
Event: OUT_GROUND
Probability: 75% → DOUBLE PLAY, 25% → Single OUT

IF DOUBLE PLAY:
  After:  r1=None, r2=None, r3=None
  Runs:   1 (r3 scores)
  Outs:   +2

Logic:
- r1 forced out at 2B
- Batter out at 1B
- r3 SCORES (forced by runner being out at 1B)
```

---

## Key Rules Implemented

1. **Force Plays**: A runner is forced to advance when:
   - A new batter hits the ball with bases loaded, OR
   - A new batter hits the ball with runner(s) ahead that must move

2. **Double Play vs. Triple Play**:
   - DP: 2 outs on one play
   - TP: 3 outs on one play (very rare, not implemented)

3. **Runner Advancement on GIDP**:
   - r1 → OUT at 2B (force)
   - r2 → Stays at 2B or advances to 3B depending on scenario
   - r3 → SCORES (if bases loaded)

4. **Probability Adjustment**:
   - 75% with runner on 1B only
   - 65% with runners on 1B and 2B (harder defense)

---

## Current Implementation Details

```python
# In runner_manager.py::advance_runners()

if event == "OUT_GROUND" and r1 is not None:
    dp_chance = 0.75
    if r2 is not None:
        dp_chance = 0.65
    
    if random.random() < dp_chance:
        # DOUBLE PLAY occurs
        if r3:
            runs = 1  # r3 scores
        else:
            runs = 0
        
        new_runners = {
            "1b": None,              # Batter out
            "2b": None,              # r1 out at 2B
            "3b": r2 if r2 else None # r2 stays (or None if no r2)
        }
        event_adjusted = "DOUBLE_PLAY"
    else:
        # Single out only
        new_runners = {"1b": r1, "2b": r2, "3b": r3}
```

---

## Testing Scenarios

### Test 1: r1 only
- Input: `{"1b": "ALICE", "2b": None, "3b": None}`, event="OUT_GROUND"
- Expected (65% chance): `{"1b": None, "2b": None, "3b": None}`, runs=0, event="DOUBLE_PLAY"

### Test 2: r1 and r2 ⭐
- Input: `{"1b": "ALICE", "2b": "BOB", "3b": None}`, event="OUT_GROUND"
- Expected (35% chance): `{"1b": None, "2b": "BOB", "3b": None}`, runs=0, event="DOUBLE_PLAY"

### Test 3: Bases loaded ⭐
- Input: `{"1b": "ALICE", "2b": "BOB", "3b": "CHARLIE"}`, event="OUT_GROUND"
- Expected (35% chance): `{"1b": None, "2b": "BOB", "3b": None}`, runs=1, event="DOUBLE_PLAY"

---

## Related Code

- **calculator.py**: Generates `OUT_GROUND` event
- **state_manager.py**: Calls `advance_runners()` to get final event and runs
- **gameplay.py**: Records event and runs to database
- **stats_recorder.py**: Counts double plays in box score

---

## Historical Fixes

### Commit c83b8f3 (Previous)
- Fixed DP advancement logic
- Added defensive dict key validation

### Commit [CURRENT]
- Fixed r2 advancement logic when bases 1B & 2B
- Clarified: r2 does NOT advance to 3B on DP when only r1 and r2 are on
- r2 stays at 2B (the force is broken after r1 is out)
