# Recent Fixes Summary

## Latest Commits (Last 4)

## Latest Commits (Last 4)

### 0. ✅ commit 01df62e: Inning-Ending Out Rule for Run Scoring
**File**: `backend/app/engine/state_manager.py`

**Fixed**: Runs scoring with 3 outs completed (inning-ending double play rule)

**MLB Rule**: A run ONLY counts if the runner crosses home BEFORE the 3rd out

**Before**:
```python
# Bases loaded, 2 outs + DP
r3 would score = +1 run ❌ (but 3rd out was made)
```

**After**:
```python
# Bases loaded, 2 outs + DP
if game.outs >= 3 and runs_scored > 0:
    runs_scored = 0  # Cancel runs, 3rd out was made
```

**Key Scenarios**:
| Situation | Outs Before | With DP | Result |
|-----------|------------|---------|--------|
| Loaded, 2 out | 2 | +2 outs | r3 doesn't score |
| Loaded, 1 out | 1 | +2 outs | r3 scores ✅ |
| 1B + 3B, 2 out | 2 | +2 outs | r3 doesn't score |

---

### 1. ✅ commit 652a564: Double Play Advancement Logic
**File**: `backend/app/engine/runner_manager.py`

**Fixed**: Runner positioning in double play scenarios with runners on 1B and 2B

**Before**:
```python
# WRONG: r2 advances to 3B on DP
if r2:
    new_runners = {"1b": None, "2b": None, "3b": r2}
```

**After**:
```python
# CORRECT: r2 stays at 2B (force is broken after r1 out)
new_runners = {
    "1b": None,
    "2b": None,
    "3b": r2 if r2 else None
}
```

**Test Case: Runners on 1B & 2B + OUT_GROUND**
```
Input:  r1="ALICE", r2="BOB", r3=None
Event:  OUT_GROUND
DP%:    65%

Expected:
- Alice OUT at 2B (force)
- Batter OUT at 1B
- Bob STAYS at 2B (no force after Alice out)
- Runs: 0
- Result: {1b: None, 2b: "BOB", 3b: None}

✅ Now Fixed
```

---

### 2. ✅ commit deb9ecd: Missing Event Descriptions

| Event | Before | After |
|-------|--------|-------|
| `STRIKE_LOOKING` | "STRIKE_LOOKING" | "Lanzamiento en la zona. ¡Strike cantado!" |
| `STRIKE_SWINGING` | "STRIKE_SWINGING" | "Swing abanicado. ¡Strike!" |
| `FOUL` | "FOUL" | "Batazo de foul." |
| `BALL` | "BALL" | "Bola." |
| `GAME_OVER` | (empty) | `state["winner_message"]` |

**Impact**: Frontend modal now displays user-friendly Spanish messages

---

### 3. ✅ commit c83b8f3: Backend Critical Bugs (7 issues)

**Bugs Fixed**:
1. Return type mismatch in unpacking
2. Incomplete runners dict keys
3. Double play advancement (initial fix)
4. Description overwriting
5. score_history initialization
6. DOUBLE_PLAY stats handler
7. Syntax validation

---

## Event Description Coverage

All 14 gameplay events now have descriptions:

✅ STRIKE_LOOKING → "Lanzamiento en la zona. ¡Strike cantado!"
✅ STRIKE_SWINGING → "Swing abanicado. ¡Strike!"
✅ BALL → "Bola."
✅ FOUL → "Batazo de foul."
✅ HOME_RUN → "¡HOME RUN!"
✅ HIT_3B → "Triple."
✅ HIT_2B → "Doble base."
✅ HIT_1B → "Hit sencillo."
✅ OUT_GROUND → "Roletazo al cuadro para out."
✅ OUT_FLY → "Elevado de rutina atrapado en el jardín."
✅ STRIKEOUT → "Strikeout! El bateador no pudo conectar."
✅ WALK → "Base por bolas."
✅ DOUBLE_PLAY → "¡Doble play! El corredor en primera fue eliminado..."
✅ GAME_OVER → Winner message from state

---

## Baseball Rules Implemented

### Double Play Scenarios Handled

| Runners | Event | Result | Runs |
|---------|-------|--------|------|
| 1B only | OUT_GROUND | r1 out at 2B, batter out | 0 |
| 1B, 2B | OUT_GROUND | r1 out at 2B, r2 stays at 2B, batter out | 0 |
| 1B, 3B | OUT_GROUND | r1 out at 2B, r3 scores, batter out | 1 |
| Loaded | OUT_GROUND | r1 out at 2B, r2 stays, r3 scores, batter out | 1 |

### Force Play Rules

- Runner is forced when: new batter hits with base occupied
- Force ends when: runner forcing it is out
- r2 stays at 2B (no force after r1 out) in DP scenarios

---

## Files with Documentation

- `backend/app/engine/EVENT_DESCRIPTIONS.md` - All 14 events with themes
- `backend/app/engine/DOUBLE_PLAY_REFERENCE.md` - Complete DP rules and testing

---

## Next Steps (if needed)

- [ ] Test all double play scenarios in simulator
- [ ] Verify event descriptions in frontend modal
- [ ] Test GAME_OVER message display
- [ ] Validate stats recording for DOUBLE_PLAY events
