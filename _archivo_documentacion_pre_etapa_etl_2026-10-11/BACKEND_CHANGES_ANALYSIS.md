# 📊 Análisis de Cambios en el Backend - Commit a2324c6

## 🎯 Objetivo General
**Refactoring SOLID Fase 1-2**: Separación clara de responsabilidades, extracción de lógica del router al engine, eliminación de dependencias circulares y mejora de mantenibilidad.

**Reducción de líneas:**
- `gameplay.py`: ~1,341 → ~800 líneas (-541 líneas)
- Total del módulo: 233 insertions(+), 219 deletions(-)

---

## ✅ Cambios Principales

### 1. 🆕 NUEVO: `backend/app/engine/steal_actions.py`
**Responsabilidad:** Lógica pura del robo de base (sin FastAPI, sin BD, sin broadcasts)

**Funciones:**
- `steal_attempt(game, state, target_base, pitcher_attrs)` 
  - Ejecuta intento de robo (2B/3B)
  - Muta `game` y `state` con consecuencias
  - Retorna `(success, description)`
  - Maneja cambio de media entrada si se alcanza 3 outs
  - Verifica fin de juego

**Arquitectura:**
```
Router (HTTP) 
  ↓
steal_attempt() [PURO - sin FastAPI]
  ├─ resolve_steal() [tácticas]
  ├─ end_half_inning() [state manager]
  └─ check_game_over() [regla de fin]
  ↑
(commit y broadcast es responsabilidad del router)
```

**Benefit:** Testeable sin FastAPI; lógica del dominio aislada.

---

### 2. 🆕 NUEVO: `backend/app/services/team_ratings.py`
**Responsabilidad:** Cálculo centralizado de medias de equipo (OVR)

**Funciones:**
- `compute_team_ratings(cards, default=70)`
  - Calcula OVR general, OVR bateo, OVR pitcheo
  - Acepta secuencia de PlayerCardModel
  - Usa regla `is_pitcher` para clasificar

- `compute_lineup_ratings(slots, default=70)`
  - Calcula OVR a partir de `UserLineup.slots` (JSON)
  - Detecta pitcher por slot "P" o `PITCHER_POSITIONS`
  - Retorna `{"overall": X, "batOvr": Y, "pitOvr": Z}`

**Uso actual:**
```python
# Antes: fórmula duplicada en routers/teams.py y routers/user.py
bat_ovr = sum(batter_overalls) / len(batter_overalls)  # ← DUPLICADO

# Ahora: única fuente de verdad
ratings = compute_lineup_ratings(slots)  # ← CENTRALIZADO
```

**Benefit:** Un cambio de balance se hace en un solo lugar; no hay fórmulas inconsistentes.

---

### 3. 📝 REFACTOR MASIVO: `backend/app/engine/game_actions.py`
**Cambio:** Extracción de 370+ líneas de lógica desde `gameplay.py` al engine.

#### Nuevo: `build_play_resolved_payload()`
**Responsabilidad:** Construir el payload estándar de WebSocket para `PLAY_RESOLVED`

**Incluye:**
```python
{
  "type": "PLAY_RESOLVED",
  "event": event,
  "description": description,
  
  # ⭐ DATOS CRÍTICOS DEL GAMEPLAY
  "outs": game.outs,
  "balls": game.balls,
  "strikes": game.strikes,
  "score_home": game.score_home,
  "score_away": game.score_away,
  "current_inning": game.current_inning,
  "is_top_inning": game.is_top_inning,
  
  # ⭐ ESTADÍSTICAS (NUEVO)
  "pitcher_strikeouts": {...},  # Por pitcher
  "batter_stats": {...},         # Hits, RBIs, etc.
  "home_hits": X,
  "away_hits": Y,
  "inning_runs": {...},          # Carreras por inning
  
  # ⭐ TARJETAS ACTIVAS (NUEVO)
  "active_pitcher": {...},       # Datos completos del lanzador
  "active_batter": {...},        # Datos completos del bateador
  
  "state_data": state_with_role,
  "inning_completed": inning_ended,
}
```

**Datos Mejorados:**
- `pitcher_strikeouts`: Strikeouts por cada pitcher (recuperados de DB)
- `batter_stats`: Hits, doubles, home_runs, RBIs, etc.
- `home_hits` / `away_hits`: Total de hits por equipo
- `inning_runs`: Carreras en cada inning (desde `score_history`)
- `active_pitcher`: Nombre, OVR, pitch count, fatigue level, repertorio
- `active_batter`: Nombre, OVR, contact, power, attributes

**Benefit:** Frontend recibe todos los datos de una sola vez; no necesita llamadas extras.

#### Nuevo: `perform_pitcher_change()`
**Responsabilidad:** Regla compartida de cambio de pitcher (humano o CPU)

```python
def perform_pitcher_change(game, state, new_pitcher_id, is_home):
    """
    - Registra nuevo pitcher como activo
    - Actualiza field (home/away_pitcher_id) para restauración de inning
    - Resetea pitch count del nuevo pitcher
    - Retorna old_pitcher_id
    """
```

**Uso:** Tanto `change_pitcher_endpoint` como `execute_cpu_pitcher_change` usan esta regla.

#### Mejorado: `resolve_swing()`
**Cambios:**
```python
# ANTES: ~120 líneas en gameplay.py con validaciones HTTP

# AHORA: función pura de 6 fases
async def resolve_swing(
    game, state, swing_type, guessed_zone, guessed_pitch, 
    db, game_id, user_id=None  # ⭐ NUEVO: user_id para user_role
):
    # 1. Fatiga del pitcher
    # 2. Obtener atributos reales desde BD
    # 3. Procesamiento especial de BUNT
    # 4. Modificadores de tácticas
    # 5. Calcular resultado
    # 6. Transición de estado + estadísticas + broadcast
```

**Improvements:**
- Recibe `user_id` (para incluir en payload y sanitizar state por destinatario)
- Recupera `pitch_specific_stats` del repertorio real del pitcher
- Calcula `fatigue_level` con `compute_fatigue_level()` (dinámico por innings)
- Broadcast vía `_play_resolved_for(recipient_user_id)` → **Fog of War por destinatario**

#### Nuevo: `execute_cpu_pitcher_change()`
**Responsabilidad:** Cambio de pitcher de la CPU con decisión + selecc.

```python
async def execute_cpu_pitcher_change(game, state, db, game_id, difficulty):
    # 1. Validar que hay CPU en el juego
    # 2. Buscar relevistas disponibles (no usados)
    # 3. Seleccionar el de mayor OVR
    # 4. Ejecutar cambio con perform_pitcher_change()
    # 5. Setear flags de acknowledment pendiente
    # 6. Broadcast PITCHER_CHANGED con datos sanitizados
    return True/False
```

**Flags nuevos:**
```python
state["awaiting_pitcher_change_acknowledgment"] = True
state["pending_pitcher_change"] = {
    "old_pitcher_id": ...,
    "new_pitcher_id": ...,
}
```

#### Mejorado: `trigger_cpu_response()`
**Cambios:**
- Evalúa si CPU debe **cambiar pitcher** (antes de pichear)
- Llama `execute_cpu_pitcher_change()` si es necesario
- Usa `compute_fatigue_level()` para decisión dinámina
- Selecciona pitch type desde **repertorio real** de la tarjeta

**Flujo:**
```
CPU pitcher turn (no hay pitch pendiente)
  ├─ Evaluar fatiga del pitcher activo
  ├─ Decidir si cambiar pitcher
  │   └─ execute_cpu_pitcher_change() → broadcast PITCHER_CHANGED
  └─ Seleccionar pitch type desde repertorio real
```

---

### 4. 📝 REFACTOR: `backend/app/routers/gameplay.py`
**Cambio:** Reducción de 541 líneas (mudanza de lógica a `game_actions.py`)

**Antes (linea 785-880):**
```python
@router.post("/{game_id}/swing")
def execute_swing(game_id, payload, current_user_id, db):
    # ❌ 95+ líneas de lógica del engine
    # ❌ Cálculos de fatiga
    # ❌ Resolver swing
    # ❌ Actualizar stats
    # ❌ Broadcast WS
```

**Ahora:**
```python
@router.post("/{game_id}/swing")
async def execute_swing(game_id, payload, current_user_id, db):
    # ✅ Validaciones HTTP
    # ✅ Persistencia (commit)
    # ✅ Llamada a resolve_swing()
```

**Responsabilidades Finales del Router:**
1. Autenticación (JWT)
2. Validación HTTP (schemas)
3. Unit of Work (commit/rollback)
4. Manejo de errores HTTP (HTTPException)

**Responsabilidades del Engine (game_actions.py):**
1. Lógica del dominio (resolve_swing, pitcher change)
2. Broadcast WS
3. Cálculos compartidos (fatiga, OVR, pitch counts)

---

### 5. 📝 REFACTOR: `backend/app/core/enums.py`
**Nuevo:** Posiciones SU/CL

```python
class PitcherPosition(Enum):
    SP = "SP"  # Starter (Abridor)
    RP = "RP"  # Relief Pitcher
    SU = "SU"  # Setup Man (Nuevo)
    CL = "CL"  # Closer (Nuevo)
    TWP = "TWP"  # Two-way Player
```

**Benefit:** Posiciones más específicas para bullpen en futuras mejoras.

---

### 6. 📝 CAMBIOS: `backend/app/repositories/game_stats_repository.py`
**Cambio:** Refactoring de queries para soportar mejor acceso a estadísticas

**Funciones mejoradas:**
- `get_game_box_score()`: Acceso uniforme a strikeouts, hits, stats
- Ahora retorna estructura consistente para `pitcher_strikeouts`, `batter_stats`, etc.

---

### 7. 📝 CAMBIOS: `backend/app/routers/user.py`
**Cambio:** Uso de `team_ratings.compute_lineup_ratings()` en lugar de fórmula local

**Antes:**
```python
# ❌ 20+ líneas de cálculo OVR
def get_user_overall(lineup):
    batter_ov = sum(...) / len(...)
    pitcher_ov = sum(...) / len(...)
    return (batter_ov + pitcher_ov) / 2
```

**Ahora:**
```python
# ✅ Una línea centralizada
ratings = compute_lineup_ratings(lineup.slots)
return ratings["overall"]
```

---

### 8. 📝 CAMBIOS: `backend/app/routers/teams.py`
**Cambio:** Mismo refactoring que en `user.py`

---

### 9. 📝 CAMBIOS: `backend/app/routers/games.py`
**Cambio:** Actualización de llamadas a endpoints movidos/refactorados

---

## 🏗️ Patrones SOLID Aplicados

### Single Responsibility Principle (SRP)
✅ `game_actions.py` → lógica del juego (sin HTTP)
✅ `gameplay.py` → HTTP + Unit of Work
✅ `team_ratings.py` → cálculo OVR (sin deps de router)
✅ `steal_actions.py` → lógica pura del robo

### Dependency Inversion Principle (DIP)
✅ `resolve_swing()` no importa FastAPI
✅ `perform_pitcher_change()` es agnóstico a origen (humano o CPU)
✅ Funciones puras aceptan argumentos, no leen del contexto HTTP

### Don't Repeat Yourself (DRY)
✅ `compute_team_ratings()` centraliza fórmula OVR
✅ `perform_pitcher_change()` regla compartida
✅ `build_play_resolved_payload()` payload único

---

## 🔄 Impacto en el Flujo de Juego

### Antes (monolítico):
```
POST /pitch → gameplay.py (550+ líneas)
  ├─ validar turno
  ├─ calcular fatiga (INCRUSTADO)
  ├─ resolver swing (INCRUSTADO)
  ├─ actualizar stats (INCRUSTADO)
  └─ broadcast (INCRUSTADO)
```

### Ahora (separado):
```
POST /pitch → gameplay.py (80 líneas)
  ├─ Validar turno
  ├─ resolve_swing() ← game_actions.py (PURO)
  │   ├─ apply_pitcher_fatigue()
  │   ├─ calculate_play_outcome()
  │   ├─ process_at_bat_transition()
  │   ├─ record_game_event()
  │   └─ build_play_resolved_payload()
  ├─ db.commit() (Unit of Work)
  └─ return HTTP response
```

---

## 📊 Estadísticas de Cambio

| Métrica | Antes | Después | Cambio |
|---------|-------|---------|--------|
| **gameplay.py** | 1,341 líneas | ~800 líneas | -541 líneas (-40%) |
| **Funciones en game_actions.py** | 0 | 6 funciones nuevas | +6 |
| **Servicios centralizados** | 0 | 1 (team_ratings.py) | +1 |
| **Módulos de dominio puro** | 0 | 1 (steal_actions.py) | +1 |
| **Dependencias FastAPI en engine** | ❌ Sí (circular) | ✅ No | ✅ Fixed |

---

## 🚀 Beneficios Inmediatos

1. **Testabilidad:** `resolve_swing()` y `steal_attempt()` son pure functions → unit tests sin contexto HTTP
2. **Mantenibilidad:** Cambio de lógica OVR → editar 1 archivo (team_ratings.py)
3. **Claridad:** Responsabilidades definidas (router = HTTP, engine = dominio)
4. **Performance:** Menos llamadas a BD (payload único con stats completas)
5. **Escalabilidad:** Reuso de funciones puras en futuros refactorings

---

## ⚠️ Consideraciones Técnicas

### Fog of War
- Implementado en `resolve_swing()` con `_play_resolved_for(recipient_user_id)`
- Cada cliente recibe su propia vista del `state_data` (pitcher enemigo oculto, etc.)

### Persistencia
- Las funciones del engine **NO commitean**
- Responsabilidad del router (Unit of Work)
- Garantiza transacciones atómicas

### Pitch Counts y Fatiga
- `pitch_counts` mutable en `state_data` (persiste en BD)
- `compute_fatigue_level()` dinámico por total de innings
- Mejora la escalabilidad a extrainnings

---

## 🔜 Próximas Mejoras Sugeridas

1. **Inyección de dependencias:** Usar DI container para reducir parámetros
2. **Value Objects:** Crear `PitchCount`, `FatigueLevel` como tipos
3. **Event Sourcing:** Reemplazar `record_game_event()` con domino events
4. **Validator Pattern:** Extraer validaciones HTTP a middleware
