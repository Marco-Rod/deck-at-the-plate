# Event Descriptions Reference

This document lists all possible gameplay events and their Spanish descriptions.

## Source Locations

- **Calculator Events**: `backend/app/engine/calculator.py::calculate_play_outcome()`
- **State Manager Descriptions**: `backend/app/engine/state_manager.py::process_at_bat_transition()` (lines 239-270)
- **Frontend Display**: `frontend/src/components/stadium/PlayResultOverlay.tsx`

---

## All 14 Event Types with Descriptions

### Pitch Outcome Events (from calculator.py)

| Event Key | Description | Duration | Epic |
|-----------|-------------|----------|------|
| `BALL` | "Bola." | 1.8s | ❌ |
| `STRIKE_LOOKING` | "Lanzamiento en la zona. ¡Strike cantado!" | 2.0s | ❌ |
| `STRIKE_SWINGING` | "Swing abanicado. ¡Strike!" | 2.0s | ❌ |
| `FOUL` | "Batazo de foul." | 1.8s | ❌ |

### Hit Events (from calculator.py → state_manager transformations)

| Event Key | Description | Duration | Epic |
|-----------|-------------|----------|------|
| `HOME_RUN` | "¡HOME RUN!" | 3.5s | ✅ |
| `HIT_3B` | "Triple." | 3.0s | ✅ |
| `HIT_2B` | "Doble base." | 2.8s | ❌ |
| `HIT_1B` | "Hit sencillo." | 2.5s | ❌ |

### Out Events (from calculator.py → state_manager transformations)

| Event Key | Description | Duration | Epic |
|-----------|-------------|----------|------|
| `OUT_GROUND` | "Roletazo al cuadro para out." | 2.5s | ❌ |
| `OUT_FLY` | "Elevado de rutina atrapado en el jardín." | 2.5s | ❌ |

### Accumulated Count Events (from state_manager.py transformations)

| Event Key | Description | Duration | Epic |
|-----------|-------------|----------|------|
| `STRIKEOUT` | "Strikeout! El bateador no pudo conectar." | 2.8s | ✅ |
| `WALK` | "Base por bolas." | 2.5s | ❌ |

### Game Mechanics Events (from state_manager.py)

| Event Key | Description | Duration | Epic |
|-----------|-------------|----------|------|
| `DOUBLE_PLAY` | "¡Doble play! El corredor en primera fue eliminado y el bateador también." | 3.0s | ✅ |
| `GAME_OVER` | `state["winner_message"]` or "¡Fin del juego!" | 3.5s | ✅ |

---

## Event Generation Flow

```
1. Pitch thrown
   ↓
2. calculator.py::calculate_play_outcome() 
   - Returns: BALL, STRIKE_LOOKING, STRIKE_SWINGING, FOUL, HOME_RUN, HIT_*, OUT_*, etc.
   ↓
3. state_manager.py::process_at_bat_transition()
   - Counts strikes/balls
   - If strikes >= 3 → transforms to STRIKEOUT
   - If balls >= 4 → transforms to WALK
   - If runners + OUT_GROUND → possibly DOUBLE_PLAY
   - If game ends → GAME_OVER
   ↓
4. Generate description from final_event
   - Each event has hardcoded Spanish description (lines 239-270)
   ↓
5. Return: (at_bat_ended, inning_ended, final_event, description)
   ↓
6. Frontend receives via WebSocket
   - PlayResultOverlay displays description
   - theme determined by resultEvent
```

---

## Bug History

### Fixed in commit deb9ecd
- **STRIKE_LOOKING**: Was returning key name → now returns description
- **STRIKE_SWINGING**: Was returning key name → now returns description
- **FOUL**: Was returning key name → now returns description
- **BALL**: Was returning key name → now returns description
- **GAME_OVER**: Was returning empty → now returns winner_message

### Fixed in commit c83b8f3
- DOUBLE_PLAY advancement logic corrected
- Runners dict keys initialization added
- Description overwriting in gameplay.py removed

---

## Frontend Integration

The `PlayResultOverlay` component (frontend/src/components/stadium/PlayResultOverlay.tsx):

1. **Receives**: `resultText` (description), `resultEvent` (event key)
2. **Selects theme**: EVENT_THEMES[resultEvent]
3. **Displays**: 
   - Large label from theme
   - Description as `{currentText}` (line 280)
   - Audio cues via playEventSound()
4. **Visibility**: Auto-hides after theme.duration

---

## Testing Checklist

- [x] BALL event displays in modal
- [x] STRIKE_LOOKING event displays message
- [x] STRIKE_SWINGING event displays message
- [x] FOUL event displays message
- [x] HOME_RUN event displays message
- [x] DOUBLE_PLAY event displays message
- [x] STRIKEOUT event displays message
- [x] WALK event displays message
- [x] GAME_OVER displays winner message
- [x] Inning change appends " Tres outs registrados. Cambio de entrada."
- [x] All events have theme in PlayResultOverlay
- [x] All events have audio cues

---

## Notes

- Descriptions are Spanish (es-ES) for consistency with game design
- Inning changes append to description if `inning_ended=True`
- Frontend has redundant themes for events (fallback to DEFAULT_THEME if missing)
- Audio manager handles missing sounds gracefully
