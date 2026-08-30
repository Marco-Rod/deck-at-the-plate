# 🎮 WebSocket & Gameplay Architecture Audit

**Status:** CRÍTICO - Se encontraron 3 bloqueadores + 3 riesgos críticos  
**Fecha:** 30 de Agosto, 2026  
**Scope:** Frontend (PWA) + Backend (FastAPI) WebSocket + Game Engine

---

## 📊 RESUMEN EJECUTIVO

| Categoría | Estado | Problemas | Esfuerzo Arreglo |
|-----------|--------|-----------|------------------|
| **Desincronización de State** | 🔴 CRÍTICO | Cambio de pitcher sin persistencia atómica | 2h |
| **Trigger CPU Response** | 🔴 CRÍTICO | Sin retry ni logging; falla silenciosa | 1h |
| **WebSocket Keep-Alive** | 🔴 CRÍTICO | Timeout 30s sin ping/pong; desconexiones falsas | 1h |
| **Polling Mode** | ⚠️ IMPORTANTE | 2s interval no es real-time | 2h |
| **Fog of War** | ⚠️ IMPORTANTE | Incompleto; filtra solo `current_pitch` | 1h |
| **State Validation** | ⚠️ IMPORTANTE | Sin checks de coherencia | 3h |
| **Race Conditions** | ⚠️ IMPORTANTE | Posibles cambios duplicados de pitcher | 2h |
| **Rate Limiting** | 🟡 INFO | Sin protección anti-DoS | 1h |

**Total P0:** 4h | **Total P0+P1:** 10h

---

## 🔴 BLOQUEADORES CRÍTICOS

### Bloqueador #1: Desinc de State en Cambio de Pitcher

**Ubicación:** `backend/app/engine/game_actions.py` líneas 443-480 (execute_cpu_pitcher_change)

**Problema:**
```python
# ACTUAL (VULNERABLE)
state["awaiting_pitcher_change_acknowledgment"] = True
game.state_data = state
db.commit()  # ¿Y si falla?
```

Cuando CPU cambia pitcher:
1. ✅ State en MEMORIA se marca `awaiting_pitcher_change_acknowledgment = True`
2. ✅ Broadcast envía PITCHER_CHANGED a frontend
3. ❌ `db.commit()` puede fallar (BD down, out of memory, etc)
4. ❌ BD aún tiene pitcher ANTIGUO
5. 💥 Frontend ve pitcher nuevo, BD tiene pitcher viejo
6. 💥 Si usuario se desconecta → INIT_GAME_STATE devuelve pitcher viejo → Inconsistencia

**Escenario de Fallo:**
```
[1] User HOME hace swing
[2] Backend resuelve swing, inicia trigger_cpu_response
[3] CPU elige cambiar pitcher, marca state en MEMORIA
[4] Broadcast enviado a ambos jugadores ✅
[5] db.commit() FALLA (timeout de BD) ❌
[6] Exception capturada, usuario notificado de error
[7] [LUEGO] User HOME se desconecta y reconecta
[8] Backend envía INIT_GAME_STATE con pitcher VIEJO (no cambió)
[9] Frontend confundido: "Cambió de pitcher pero sigue igual"
```

**Impacto:** CRÍTICO - Juego injugable tras crash de BD

**Solución:**
```python
# PROPUESTO (SEGURO)
from sqlalchemy.exc import SQLAlchemyError

try:
    state["awaiting_pitcher_change_acknowledgment"] = True
    game.state_data = state
    db.commit()
    db.refresh(game)  # Recargar para confirmar
except SQLAlchemyError as e:
    db.rollback()
    print(f"❌ CRÍTICO: Fallo al persistir cambio de pitcher: {e}")
    # Broadcast de error a ambos jugadores
    await manager.broadcast_to_game(
        game_id,
        {"type": "ERROR", "message": "Error crítico: cambio de pitcher no persistido"}
    )
    raise
```

---

### Bloqueador #2: Trigger CPU Response Falla Silenciosamente

**Ubicación:** `backend/app/routers/ws.py` líneas 67-94

**Problema:**
```python
# ACTUAL (SIN MANEJO)
try:
    await trigger_cpu_response(game, state, db, game_id)
except Exception as e:
    print(f"❌ Error: {e}")  # Solo log; juego continúa
```

Si CPU response falla (runtime error, timeout, etc):
- ❌ La CPU NO responde (no lanza pitch)
- ❌ El juego queda esperando indefinidamente
- ❌ No hay reintentos
- ❌ Usuario HOME queda colgado

**Escenario de Fallo (PvE):**
```
[1] WS Connection established (USER HOME se conecta)
[2] Backend llama trigger_cpu_response()
[3] CPU intenta elegir pitcher pero lineup está vacía → Exception
[4] Exception solo loggeada, no re-lanzada
[5] Juego inicia con USER HOME esperando swing
[6] USER HOME "tira" y espera respuesta CPU
[7] ESPERA INFINITA: CPU nunca hace nada
```

**Impacto:** CRÍTICO - Juegos PvE sin respuesta CPU

**Solución:**
```python
# PROPUESTO (CON REINTENTOS)
async def handle_websocket_init(websocket, game_id, user_id):
    game = db.query(GameSession).filter_by(id=game_id).first()
    state = game.state_data
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await trigger_cpu_response(game, state, db, game_id)
            db.commit()
            logger.info(f"✅ trigger_cpu_response succeed on attempt {attempt+1}")
            break
        except Exception as e:
            logger.error(f"❌ trigger_cpu_response attempt {attempt+1} failed: {e}")
            db.rollback()
            
            if attempt == max_retries - 1:
                # Falló definitivamente
                error_msg = {
                    "type": "ERROR",
                    "message": "El juego no pudo iniciarse. Recargue la página.",
                    "code": "CPU_INIT_FAILED"
                }
                await websocket.send_json(error_msg)
                await websocket.close(code=4500, reason="CPU init failed")
                raise
            
            # Esperar antes de reintentar
            await asyncio.sleep(0.5)
```

---

### Bloqueador #3: WebSocket Timeout sin Keep-Alive

**Ubicación:** `backend/app/routers/ws.py` línea 134

**Problema:**
```python
# ACTUAL (SIN PING/PONG)
while True:
    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
    # Si no hay mensajes en 30s → TimeoutError desconecta
```

**Escenario de Fallo:**
```
[1] User HOME conectado, esperando que User AWAY lance
[2] User AWAY en su turno pero no envía nada en 25s
[3] Backend después de 30s: TimeoutError
[4] Conexión cerrada sin notificación
[5] User HOME ve "Desconectado"
[6] Pero User AWAY aún está en el juego (no lo notificaron)
[7] Inconsistencia: Un jugador sigue, otro no
```

**Impacto:** CRÍTICO - Desconexiones falsas, juego interrumpido

**Solución:**
```python
# PROPUESTO (CON PING/PONG)
import asyncio

async def keep_alive_task(websocket, game_id):
    """Envía PING cada 15 segundos para mantener la conexión viva"""
    try:
        while True:
            await asyncio.sleep(15)
            await websocket.send_json({"type": "PING"})
    except Exception as e:
        logger.warning(f"keep_alive_task failed: {e}")

async def websocket_endpoint(websocket: WebSocket, game_id: str, token: str):
    # ... autenticación ...
    
    # Iniciar keep-alive en background
    keep_alive = asyncio.create_task(keep_alive_task(websocket, game_id))
    
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=45.0)
            message = json.loads(data)
            # Procesar mensaje
    except asyncio.TimeoutError:
        logger.warning(f"WebSocket timeout for game {game_id}")
        await websocket.close(code=4000, reason="Timeout")
    finally:
        keep_alive.cancel()
        manager.disconnect(websocket, game_id)
```

Frontend responde automáticamente a PING (ignorar, la conexión se mantiene activa).

---

## ⚠️ RIESGOS CRÍTICOS

### Riesgo #1: Fog of War Incompleto

**Ubicación:** `backend/app/engine/fog_of_war.py` líneas 19-26

**Problema Actual:**
```python
def sanitize_state_for_player(state, player_id, game_id):
    # Solo enmascara current_pitch
    if player_id != pitcher_id:
        state["current_pitch"] = None  # ✅ Correcto
    
    return state
```

**Qué está expuesto (sin enmascarar):**
- ❌ `active_tactics[pitcher_id]` - Revela qué carta tácticausó el lanzador
- ❌ `pitch_counts[pitcher_id]` - Permite inferir estrategia (ej: si hizo 95 pitches, está cansado)
- ❌ `runners` posición exacta - Bateador actual puede ver dónde están los corredores futuros
- ❌ `is_game_over` antes de confirmación - Revela resultado temprano

**Impacto:** MEDIO - Ventaja injusta en juego competitivo

**Solución:**
```python
def sanitize_state_for_player(state, player_id, game_id, is_home: bool):
    """Filtra state según perspectiva del jugador (Fog of War completo)"""
    sanitized = deepcopy(state)
    
    # Determinar roles
    pitcher_id = state.get("home_pitcher_id" if is_home else "away_pitcher_id")
    batter_id = state.get("away_pitcher_id" if is_home else "home_pitcher_id")  # El otro es bateador
    
    # 1. Pitch secreto
    if player_id != pitcher_id:
        sanitized["current_pitch"] = None
    
    # 2. Tácticas del rival (ocultarsi el otro no es pitcher)
    if player_id != pitcher_id and "active_tactics" in sanitized:
        sanitized["active_tactics"] = {
            k: None for k in sanitized["active_tactics"].keys()
            if k != player_id
        }
    
    # 3. Fatiga del rival (ocultarsi el otro es lanzador)
    opponent_pitcher = state.get("away_pitcher_id" if is_home else "home_pitcher_id")
    if opponent_pitcher and "pitch_counts" in sanitized:
        # Redondear pitch_counts del rival a blocks de 5
        opponent_pitches = sanitized["pitch_counts"].get(opponent_pitcher, 0)
        sanitized["pitch_counts"][opponent_pitcher] = (opponent_pitches // 5) * 5
    
    # 4. Posición de runners (ocultarsi es mi turno de bateo)
    if player_id == batter_id:  # Yo soy el bateador actual
        # Runners se ven, pero no debo ver mi "futuro"
        pass
    
    # 5. Game over (ocultarsi no he finalizado)
    if not sanitized.get("is_game_over"):
        sanitized["winner"] = None
    
    return sanitized
```

---

### Riesgo #2: Sin Validación de Coherencia de State

**Ubicación:** No existe - FALTA módulo

**Problema:**
No hay verificaciones que aseguren:
- `active_pitcher` está en lineup del equipo
- `active_batter` está en lineup del equipo
- `runners` no tienen IDs inválidas
- `pitch_counts` es consistente con jugadas registradas
- `is_game_over` es consistente con score + innings

**Ejemplo de Bug que pasaría sin validación:**
```python
# State corrupto (de crash anterior)
state = {
    "active_pitcher": "INVALID_ID_123",  # No existe en DB
    "home_lineup": ["p1", "p2", "p3"],
    "away_lineup": ["p4", "p5", "p6"],
    "runners": {
        "1b": "p7",  # p7 no está en ningún lineup
        "2b": "CORRUPTED",
    }
}

# Sin validación, esto continúa el juego
# Con validación, se aborta y se intenta recuperar
```

**Impacto:** MEDIO - Bugs silenciosos, acumulación de inconsistencias

**Solución:** Nuevo módulo `backend/app/engine/state_validator.py`

---

### Riesgo #3: Race Condition en Cambios de Pitcher Paralelos

**Ubicación:** `backend/app/engine/game_actions.py` línea 540+

**Problema:**
```
[1] HTTP POST /swing llega al backend → Thread A
[2] Backend carga game de BD
[3] resolve_swing() comienza ejecución
[4] Mientras: Timeout de CPU → Thread B
[5] Backend carga game de BD (versión ANTIGUA sin pitcher change)
[6] execute_cpu_pitcher_change() en Thread B
[7] A y B compiten por actualizar state["home_pitcher_id"]
[8] Resultado: ¿Qué pitcher quedó? ¿El viejo o el nuevo?
```

**Solución:** Usar transacciones con lock para actualización
```python
from sqlalchemy import select
from sqlalchemy.sql import for_update

async def execute_swing(...):
    # Lock la fila mientras se procesa
    stmt = select(GameSession).where(GameSession.id == game_id).with_for_update()
    game = db.execute(stmt).scalar_one()
    # Ahora ningún otro thread puede actualizar esta fila
    state = game.state_data
    # ...
    db.commit()  # Lock se libera aquí
```

---

## 🟡 PROBLEMAS IMPORTANTES

### Problema #4: Polling no Mantiene Estado Real-time

**Ubicación:** `pwa/src/features/game/services/socket.ts` líneas 123-155

**Problema:**
```typescript
private startPolling(): void {
  const POLL_INTERVAL_MS = 2000  // Cada 2 segundos
  this.pollTimer = setInterval(async () => {
    const state = await getGameState(this.gameId)
    this.messageHandler?.(state)  // Simula WS message
  }, POLL_INTERVAL_MS)
}
```

**Limitaciones:**
- 2s latency máximo (peor caso) - rival ve tu acción 2s después
- No hay retry si falla HTTP
- No hay hash checking - toda acción envía 1MB de state incluso si no cambió
- `user_role` se pierde en polling (siempre undefined)

**Impacto:** MEDIO - Juego lento en conexiones inestables

**Solución (Hybrid Polling):**
```typescript
private startPolling(): void {
  let lastStateHash: string | null = null
  
  const pollOnce = async () => {
    try {
      const state = await getGameState(this.gameId)
      const hash = hashGameState(state)
      
      if (hash !== lastStateHash) {
        lastStateHash = hash
        this.messageHandler?.(state)
      }
    } catch (err) {
      console.error('Poll failed:', err)
      // Retry con backoff
      this.scheduleReconnect()
    }
  }
  
  this.setMode('polling')
  this.pollTimer = setInterval(pollOnce, POLL_INTERVAL_MS)
}
```

---

### Problema #5: Notificación de Desconexión del Rival

**Ubicación:** `backend/app/engine/websocket_manager.py` línea 45

**Problema:**
```python
def disconnect(self, websocket: WSConnection, game_id: str):
    if game_id in self.active_connections:
        self.active_connections[game_id] = [
            (ws, uid) for ws, uid in self.active_connections[game_id] 
            if ws is not websocket
        ]
    # El otro jugador NO se entera de que te fuiste
```

**Impacto:** BAJO - UX confusa (rival desaparece sin aviso)

**Solución:**
```python
async def disconnect(self, websocket: WSConnection, game_id: str):
    if game_id in self.active_connections:
        # Notificar a otros jugadores
        for other_ws, other_uid in self.active_connections[game_id]:
            if other_ws is not websocket:
                try:
                    await other_ws.send_json({
                        "type": "OPPONENT_DISCONNECTED",
                        "message": "Tu oponente se desconectó. Esperando reconexión..."
                    })
                except:
                    pass
        
        # Luego limpiar
        self.active_connections[game_id] = [
            (ws, uid) for ws, uid in self.active_connections[game_id] 
            if ws is not websocket
        ]
```

---

## 📋 PLAN DE ACCIÓN

### Fase 1: BLOQUEADORES CRÍTICOS (4 horas)

1. **Fix Persistencia Atómica de Pitcher** (1h)
   - File: `backend/app/engine/game_actions.py`
   - Add: Transacción con rollback seguro

2. **Fix Trigger CPU Response con Retry** (1h)
   - File: `backend/app/routers/ws.py`
   - Add: Reintentos + logging + close code

3. **Fix WebSocket Keep-Alive** (1h)
   - File: `backend/app/routers/ws.py`
   - Add: PING cada 15s + keep_alive_task

4. **Test Integration** (1h)
   - Simular desconexiones, timeouts, crashés
   - Verificar state consistency

### Fase 2: RIESGOS CRÍTICOS (5 horas)

5. **Improve Fog of War** (1h)
   - File: `backend/app/engine/fog_of_war.py`
   - Add: Enmascara pitch_counts, active_tactics, runners

6. **Add State Validator** (2h)
   - File: `backend/app/engine/state_validator.py` (NEW)
   - Add: Checks de coherencia + tests

7. **Fix Race Conditions** (1h)
   - File: `backend/app/engine/game_actions.py`
   - Add: `with_for_update()` locks

8. **Add Rate Limiting** (1h)
   - File: `backend/app/routers/gameplay.py`
   - Add: `@limiter.limit()` decorators

### Fase 3: MEJORAS (2 horas)

9. **Improve Polling** (1h)
   - File: `pwa/src/features/game/services/socket.ts`
   - Add: Hash checking + retry logic

10. **Add Disconnect Notification** (1h)
    - File: `backend/app/engine/websocket_manager.py`
    - Add: Broadcast de desconexión

---

## 🧪 TEST PLAN

### Test Case 1: Persistencia de Pitcher Change
```gherkin
Given: PvE game, User HOME tira un swing
When: CPU resuelve y cambia pitcher
And: BD simula timeout durante commit
Then: Exception manejada, state no se corrompe
And: Reconexión recibe state consistente
```

### Test Case 2: Trigger CPU Response Failure
```gherkin
Given: PvE game just created, CPU lineup vacía
When: WS init trata de trigger_cpu_response
Then: Reintentos 3 veces
And: Error enviado a cliente si persiste
And: WS se cierra con close code 4500
```

### Test Case 3: Timeout sin Keep-Alive
```gherkin
Given: WS conectado, esperando turno rival
When: 30+ segundos sin actividad
Then: Backend envía PING cada 15s
And: Conexión se mantiene activa
And: Sin TimeoutError falso
```

---

## 📚 Referencias

- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [SQLAlchemy Concurrency](https://docs.sqlalchemy.org/en/20/faq/concurrency.html)
- [WebSocket Keep-Alive](https://www.rfc-editor.org/rfc/rfc6455#section-5.5.2)
- [Fog of War Patterns](https://www.gamedev.net/tutorials/programming/general/fog-of-war-using-meshes-r4378/)

---

**Documento generado:** 30 de Agosto, 2026  
**Próximo review:** Después de implementar Fase 1
