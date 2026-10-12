# 📋 RESUMEN DE CAMBIOS EN EL BACKEND - Commit a2324c6

## 🎯 Objetivo
**Refactoring SOLID Fase 1-2**: Separar lógica de juego (engine) del router HTTP, centralizar cálculos, y agregar características de cambio de pitcher y robo de base.

---

## 📊 ESTADÍSTICAS GENERALES

- **Archivos creados:** 2 (`steal_actions.py`, `team_ratings.py`)
- **Archivos modificados:** 8
- **Líneas removidas del router:** -541 (40% reducción en `gameplay.py`)
- **Nuevos endpoints:** 2 (`acknowledge-pitcher-change`, `box-score`)
- **Nuevas posiciones de pitcher:** SU (Setup), CL (Closer)

---

## 📁 ARCHIVOS MODIFICADOS - RESUMEN EJECUTIVO

### 🆕 NUEVOS ARCHIVOS

#### 1. `backend/app/engine/steal_actions.py` (65 líneas)
**Qué es:** Módulo de lógica pura del robo de base (sin FastAPI, sin BD)

**Función principal:** `steal_attempt(game, state, target_base, pitcher_attrs)`
- Ejecuta intento de robo (2B o 3B)
- Maneja out por robo fallido (incrementa outs)
- Detecta cambio de media entrada si outs >= 3
- Verifica fin de juego automáticamente
- Completamente testeable sin contexto HTTP

**Impacto:** Robo de base ahora es lógica compartida (no duplicada en router).

---

#### 2. `backend/app/services/team_ratings.py` (42 líneas)
**Qué es:** Servicio centralizado de cálculo de OVR (Overall Rating)

**Funciones:**
- `compute_team_ratings(cards)` → Calcula OVR general, OVR bateo, OVR pitcheo
- `compute_lineup_ratings(slots)` → Igual pero desde JSON del lineup

**Antes:**
```python
# Fórmula duplicada en routers/teams.py y routers/user.py
bat_ovr = sum(...) / len(...)  # ← PROBLEMA: 2+ lugares con misma lógica
```

**Ahora:**
```python
# Única fuente de verdad
ratings = compute_lineup_ratings(slots)  # ← UNA línea
overall = ratings["overall"]
```

**Impacto:** Cambios de balance = editar 1 archivo. No hay fórmulas inconsistentes.

---

### 📝 ARCHIVOS REFACTORADOS

#### 3. `backend/app/core/enums.py` (+4 líneas)
**Cambios:**
- Posiciones nuevas: `SETUP = "SU"`, `CLOSER_MAJOR = "CL"`
- Property `is_pitcher` ahora incluye estas nuevas posiciones
- Constante `PITCHER_POSITIONS` se actualiza automáticamente

**Impacto:** Enums como fuente única para reglas (Open/Closed Principle).

---

#### 4. `backend/app/engine/cpu_ai.py` (+52 líneas, -52 líneas)
**Cambios:**

| Función | Cambio |
|---------|--------|
| **`is_cpu_turn(game, state, required_role)`** | ✅ NUEVA - Determina si CPU debe actuar |
| **`get_cpu_pitcher_change_decision(pitch_count, fatigue_level, difficulty)`** | ✅ NUEVA - Decide si CPU cambia pitcher por fatiga |
| **`choose_pitch_from_repertoire(repertoire)`** | ✅ NUEVA - Selecciona pitch type del repertorio real |
| `get_cpu_swing_action()` | Refactorizado: ahora es simple, delega decisiones a funciones puras |
| `get_cpu_pitch_action()` | Mejorado: usa `choose_pitch_from_repertoire()` |

**Decisión de cambio de pitcher (NEW):**
```python
def get_cpu_pitcher_change_decision(pitch_count, fatigue_level, difficulty):
    # Umbrales por dificultad: EASY 95%, MEDIUM 65%, HARD 40%
    # + probabilidad aleatoria para variabilidad
    # Retorna: True/False
```

**Impacto:** CPU ahora es proactiva en cambios de pitcher. Decisiones basadas en datos (fatiga, pitch count).

---

#### 5. `backend/app/engine/game_actions.py` (NUEVO - 370+ líneas movidas aquí)
**Qué es:** Módulo que concentra TODA la lógica de juego del engine (antes dispersa en `gameplay.py`)

**Funciones principales:**

| Función | Líneas | Propósito |
|---------|--------|----------|
| `build_play_resolved_payload()` | ~80 | Construye payload WebSocket completo (con stats, active pitcher/batter) |
| `apply_tactic_modifiers()` | ~20 | Lee tácticas, acumula modificadores |
| `resolve_swing()` | ~130 | **Core del at-bat:** fatiga, cálculo, transición, estadísticas, broadcast |
| `perform_pitcher_change()` | ~15 | Regla compartida (humano/CPU): cambio de pitcher |
| `execute_cpu_pitcher_change()` | ~85 | CPU cambia pitcher: busca, selecciona, notifica |
| `trigger_cpu_response()` | ~50 | Orquesta respuesta CPU (batea o pichea) |

**Datos enriquecidos en payload (NEW):**
```python
{
  "pitcher_strikeouts": {pitcher_id: count, ...},  # Strikeouts por pitcher
  "batter_stats": {batter_id: {hits, hr, rbi, ...}},  # Stats del bateador
  "home_hits": X, "away_hits": Y,  # Total hits por equipo
  "inning_runs": {inning_num: runs, ...},  # Carreras por inning
  "active_pitcher": {name, ovr, pitch_count, fatigue_level, repertoire},  # ✅ NUEVO
  "active_batter": {name, ovr, contact, power, ...},  # ✅ NUEVO
}
```

**Fog of War (NEW):**
```python
# Cada cliente recibe su propia vista del estado
_play_resolved_for(recipient_user_id) → sanitiza state_data
```

**Impacto:** Motor desacoplado de HTTP. Testeable sin FastAPI. Payload completo reduce llamadas frontend.

---

#### 6. `backend/app/repositories/game_stats_repository.py` (Refactorizado)
**Cambios:**

| Función | Cambio |
|---------|--------|
| `record_game_event()` | ✅ NUEVA - Registra evento en BD con mapeo de nombres |
| `get_game_box_score()` | ✅ NUEVA - Calcula box score agregando eventos |
| `get_player_game_stats()` | ✅ NUEVA - Stats de un jugador en una partida |

**Antes:** Stats inline en router (mezcla de responsabilidades)
**Ahora:** Repositorio centralizado (capa de datos)

**Box score declarativo:**
```python
# Registries evitan duplicación
_BAT_KEYS_BOX = {...}  # Agregar evento = editar registry
_PITCH_KEYS = {...}    # No buscar en 10 lugares
```

**Impacto:** Persistencia separada de lógica. Queries declarativas.

---

#### 7. `backend/app/routers/gameplay.py` (-541 líneas, -40%)
**Cambios principales:**

| Aspecto | Antes | Ahora |
|--------|-------|-------|
| **Responsabilidad** | Lógica + HTTP | Solo HTTP + Unit of Work |
| **Líneas** | ~1,341 | ~800 |
| **Endpoints** | 8 | 10 (+ 2 nuevos) |
| **Validación turno** | Inline | Helper `_require_turn()` |

**Endpoints refactorados:**

1. **`POST /pitch`** - Simplificado
   - Antes: 95+ líneas de lógica
   - Ahora: Delega a `resolve_swing()` en engine
   - ✅ NUEVO: Validación de `awaiting_pitcher_change_acknowledgment` (bloquea pitch)
   - ✅ NUEVO: Llamada a `trigger_cpu_response()` para CPU swing automático

2. **`POST /swing`** - Reestructurado
   - ✅ NUEVO: Caché expunge + recarga fresh de BD (evita stale state)
   - ✅ NUEVO: Validación de `awaiting_pitcher_change_acknowledgment`
   - ✅ NUEVO: Si turno de CPU pitcher, ejecuta `trigger_cpu_response()` aquí
   - Parámetro `user_id` nuevo en `resolve_swing()`

3. **`POST /change-pitcher`** - Centralizado
   - Antes: Lógica inline (set active_pitcher, reset pitch_count)
   - Ahora: Delega a `perform_pitcher_change()` (regla compartida)
   - Broadcast `PITCHER_CHANGED` (igual que CPU)

4. **`POST /steal`** - Extraído
   - Antes: Lógica inline
   - Ahora: Delega a `steal_attempt()` de `steal_actions.py`
   - Muta `game.outs`, `state["runners"]`, detecta cambio de entrada

5. **`POST /{game_id}/acknowledge-pitcher-change`** - ✅ NUEVO ENDPOINT
   - Usuario confirma que vio cambio de pitcher de CPU
   - Limpia flags: `awaiting_pitcher_change_acknowledgment`, `pending_pitcher_change`
   - Broadcast `PITCHER_CHANGE_ACKNOWLEDGED`

**Impacto:** Router es 40% más corto. Responsabilidades claras: HTTP + persistencia.

---

#### 8. `backend/app/routers/games.py` (Mejorado)
**Cambios:**

| Aspecto | Cambio |
|---------|--------|
| **`POST /create`** | ✅ Delega a `GameSessionService.create()` (antes inline) |
| **`GET /{game_id}`** | ✅ Aplicada Fog of War (state sanitizado por rol) |
| **`GET /{game_id}/box-score`** | ✅ NUEVO - Box score completo |
| **`GET /{game_id}/player/{id}/stats`** | ✅ NUEVO - Stats del jugador en partida |

**Impacto:** Nuevos endpoints exponen datos que antes estaban ocultos. Fog of War evita leaks de información.

---

#### 9. `backend/app/routers/teams.py` (Refactorizado)
**Cambios:**

| Endpoint | Antes | Ahora |
|----------|-------|-------|
| `GET /cpu` | Cálculo inline de OVR | ✅ Usa `compute_team_ratings()` |
| Query | Probablemente N+1 | Única query de cartas + agregación |

**Antes:**
```python
# ❌ Fórmula duplicada
bat_ovr = sum(b.overall for b in batters) / len(batters)
pit_ovr = sum(p.overall for p in pitchers) / len(pitchers)
overall = (bat_ovr + pit_ovr) / 2
```

**Ahora:**
```python
# ✅ Servicio centralizado
ratings = compute_team_ratings(cards)
return ratings
```

**Impacto:** DRY - fórmula en un solo lugar.

---

#### 10. `backend/app/routers/user.py` (Refactorizado)
**Cambios:**

| Endpoint | Cambio |
|----------|--------|
| `GET /me/team-stats` | ✅ NUEVO - Calcula OVR del lineup activo |
| Cálculo OVR | ✅ Usa `compute_lineup_ratings()` |

**Impacto:** Expone OVR dinámico del usuario. DRY.

---

#### 11. `backend/app/engine/turn_guard.py` (Extraído)
**Funciones puras (sin FastAPI, sin BD):**

| Función | Propósito |
|---------|----------|
| `expected_actor(game, required_role)` | ¿Quién debe actuar? (regla: TOP pitcher=HOME, BATTER=AWAY) |
| `is_player_turn(game, user_id, required_role)` | ¿Le toca al usuario? |

**Reutilización:**
- `cpu_ai.is_cpu_turn()` usa `expected_actor()`
- `gameplay.py` router usa `is_player_turn()` + `_require_turn()` helper
- **Única fuente de verdad**: una regla en un lugar

**Impacto:** Turno centralizado. Evita inconsistencias (TOP pitcher ≠ AWAY, etc).

---

## 🔄 FLUJO DE JUEGO - CAMBIOS OPERACIONALES

### Antes (sin cambio de pitcher bloqueante):
```
CPU pitcher change decision → Cambio automático → Juego continúa
                             (sin confirmación humana)
```

### Ahora (con acknowledment):
```
CPU pitcher change decision 
  → execute_cpu_pitcher_change()
  → State: awaiting_pitcher_change_acknowledgment = True
  → Broadcast PITCHER_CHANGED
  → Pitch endpoint: BLOQUEADO (retorna 403)
  ← Usuario recibe modal
  ← Usuario hace click "Entendido"
  → POST /acknowledge-pitcher-change
  → State: awaiting_pitcher_change_acknowledgment = False
  → Juego continúa
```

### CPU behavior mejorado:
```
Humano pichea (TOP)
  → CPU detecta fatiga con get_cpu_pitcher_change_decision()
  → Si decide: execute_cpu_pitcher_change() + broadcast
  ← (espera ack)
  → CPU batea (resolve_swing automático)

Humano batea (BOTTOM)
  → CPU detecta turno de pitcher
  → Trigger CPU pitcher → CPU pichea automáticamente
  ← Humano recibe pitch
  → Humano hace swing
```

---

## 🏗️ PRINCIPIOS SOLID APLICADOS

### ✅ Single Responsibility Principle (SRP)
- **Router (`gameplay.py`):** HTTP + validación + persistencia
- **Engine (`game_actions.py`):** Lógica del juego
- **Repositorio (`game_stats_repository.py`):** Acceso a datos
- **Servicio (`team_ratings.py`):** Cálculos compartidos

### ✅ Open/Closed Principle
- **Enums:** Agregar posición SU/CL = editar 1 enum, no 10 archivos
- **Registries:** `_BAT_KEYS_BOX`, `_PITCH_KEYS` declarativos

### ✅ Dependency Inversion Principle
- **`turn_guard.py`:** Lógica pura, sin deps
- **`steal_actions.py`:** Puro (sin FastAPI, sin BD)
- **`game_actions.py`:** Sin importar FastAPI
- **Router usa estos:** Depende de abstracciones, no de implementación

### ✅ Don't Repeat Yourself (DRY)
- **OVR:** Una fórmula en `team_ratings.py`
- **Pitcher change:** Regla en `perform_pitcher_change()`
- **Turno:** Lógica en `turn_guard.py`

---

## 📊 IMPACTO EN FRONTEND

El frontend recibe MÁS datos completos en cada `PLAY_RESOLVED`:

**Nuevos campos:**
```javascript
{
  pitcher_strikeouts: {pitcher_id: count},
  batter_stats: {batter_id: {hits, hr, ...}},
  home_hits, away_hits,
  inning_runs,
  active_pitcher: {name, ovr, pitch_count, fatigue_level, repertoire},
  active_batter: {name, ovr, contact, power, ...}
}
```

**Ya está implementado en localStorage persistence**, así que el frontend debería estar capturando estos datos automáticamente en cada evento.

---

## 🔐 SEGURIDAD Y BLOQUEOS

### Nuevo: Bloqueo de pitcher change
- Si `awaiting_pitcher_change_acknowledgment = True`
- POST `/pitch` retorna **403 FORBIDDEN**
- POST `/swing` retorna **403 FORBIDDEN**
- ✅ **Validación server-side** (seguro, no puede bypassearse con DevTools)

### Fog of War
- Cada cliente recibe `state_data` sanitizado según su rol
- Pitcher enemigo oculto, corredores secretos, etc.
- Implementado en `_play_resolved_for(recipient_user_id)`

---

## 🎯 CASOS DE USO CUBIERTOS

1. ✅ **Cambio de pitcher por fatiga (CPU)** - Bloqueante con acknowledment
2. ✅ **Cambio de pitcher manual (humano)** - Same flow como CPU
3. ✅ **Robo de base** - Lógica centralizada, testeable
4. ✅ **Turno correcto** - Validación centralizada
5. ✅ **OVR dinámico** - Servicio único
6. ✅ **Stats en tiempo real** - Payload completo
7. ✅ **Fog of War** - Per-recipient sanitization

---

## ⚠️ CONSIDERACIONES TÉCNICAS

### Unit of Work Pattern
- Engine NO commitea
- Router es dueño de transacción (commit/rollback)
- Garantiza consistencia atomicidad

### Caché y Fresh Reads
- `db.expunge_all()` antes de recarga en algunos endpoints
- Evita stale state después de operaciones paralelas

### Fatiga Dinámica
- `compute_fatigue_level(pitch_count, total_innings)`
- Escalable a extrainnings (umbral no es hardcoded)

---

## 🔜 PRÓXIMOS PASOS SUGERIDOS

1. **Validar flujo de cambio de pitcher** en UI (modal, bloqueos)
2. **Verificar Fog of War** - ¿Se oculta info del pitcher enemigo?
3. **Testear robo de base** - ¿Funciona fin de media entrada?
4. **Testing de OVR** - ¿Medias calculadas correctamente?
5. **Performance** - ¿Box score con muchos eventos es rápido?
