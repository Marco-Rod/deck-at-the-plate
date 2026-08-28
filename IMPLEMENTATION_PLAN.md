# Event Sequencer Implementation Plan

## Resumen Ejecutivo
Implementar un sistema de **Event Queue Manager** que ordene y secuencie todos los eventos del gameplay para mejorar la UX y narrativa del juego.

**Cambio principal:** De actualizaciones caóticas a una secuencia controlada donde:
1. El usuario VE el evento (modal)
2. Luego VE cómo cambia la UI (scores, stats, runners, etc.)
3. Todo en el orden correcto y con timing perfecto

---

## Archivos a Modificar

### 1. **NEW: `frontend/src/hooks/useEventSequencer.ts`** ✅ HECHO
- Hook principal para gestionar la queue de eventos
- Define `EVENT_SEQUENCES` con timing de cada tipo de evento
- Ejecuta callbacks en el orden correcto
- Status: **CREADO**

### 2. **MODIFY: `frontend/src/hooks/useStadiumSocket.ts`**
**Cambio:** Dejar de actualizar state directamente. En su lugar, encolar eventos.

**De:**
```typescript
case 'PLAY_RESOLVED': {
  const payload = data as PlayResolvedPayload;
  setLastResult({ text: payload.description, event: payload.event, ts: Date.now() });
  setTimeout(() => {
    setGameState(parseStateData(payload));
    setHasPitched(false);
    if (payload.inning_completed) {
      setInningCompleted({ ts: Date.now() });
    }
  }, 300);
  break;
}
```

**A:**
```typescript
case 'PLAY_RESOLVED': {
  const payload = data as PlayResolvedPayload;
  
  // No actualizar state aquí
  // Simplemente encolar el evento
  // El hook useEventSequencer se encargará del rest
  
  // Pasar al componente padre que lo enquee
  onPlayResolved?.(payload);
  
  break;
}
```

**Acción:** Cambiar el hook para que sea más pasivo (solo recibe, no procesa)

---

### 3. **MODIFY: `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`** (Mayor)

**Cambios necesarios:**

#### 3a. Agregar import del hook
```typescript
import { useEventSequencer, EVENT_SEQUENCES } from '../../hooks/useEventSequencer';
```

#### 3b. Inicializar el hook
```typescript
const { enqueueEvent, queue, currentEvent, isProcessing, onStep } = useEventSequencer();
```

#### 3c. Registrar callbacks para cada step
```typescript
// Registrar qué sucede en cada step del evento
useEffect(() => {
  onStep('show-modal', (payload, stepName) => {
    setLastResult({ 
      text: payload.description, 
      event: payload.event, 
      ts: Date.now() 
    });
  });
}, [onStep]);

useEffect(() => {
  onStep('update-score', (payload) => {
    setGameState(prev => ({
      ...prev,
      homeScore: payload.score_home,
      awayScore: payload.score_away,
    }));
  });
}, [onStep]);

useEffect(() => {
  onStep('update-batter-stats', (payload) => {
    // Actualizar stats del bateador
  });
}, [onStep]);

// ... más steps
```

#### 3d. Handlers del WebSocket
```typescript
const handlePlayResolved = (payload: PlayResolvedPayload) => {
  // Determinar el tipo de evento
  const eventType = payload.event.toUpperCase(); // 'HOME_RUN', 'STRIKEOUT', etc.
  
  // Encolar el evento
  enqueueEvent(eventType as keyof typeof EVENT_SEQUENCES, payload);
};

const handlePitcherChanged = (payload: any) => {
  enqueueEvent('PITCHER_CHANGED', payload);
};
```

#### 3e. Modificar WebSocket handler
```typescript
// En useStadiumSocket o como callback:
<useStadiumSocket 
  gameId={gameId}
  userId={userId}
  onPlayResolved={handlePlayResolved}
  onPitcherChanged={handlePitcherChanged}
/>
```

#### 3f. Deshabilitar controles mientras hay evento activo
```typescript
const isEventActive = isProcessing; // o currentEvent !== null

// Pasar a CentralField, TacticalHand, etc.
<CentralField disabled={isEventActive} />
<TacticalHand disabled={isEventActive} />
```

---

### 4. **MODIFY: `frontend/src/hooks/useStadiumSocket.ts`** (Menor)

**Cambio:** El hook necesita aceptar callbacks para eventos

```typescript
interface UseStadiumSocketOptions {
  onPlayResolved?: (payload: PlayResolvedPayload) => void;
  onPitcherChanged?: (payload: any) => void;
  onInningCompleted?: (payload: any) => void;
  onGameOver?: (payload: any) => void;
}

export const useStadiumSocket = (
  gameId: string,
  userId: string,
  options: UseStadiumSocketOptions = {}
): UseStadiumSocketReturn => {
  // ...
  
  case 'PLAY_RESOLVED': {
    const payload = data as PlayResolvedPayload;
    options.onPlayResolved?.(payload);  // ← Callback
    break;
  }
  
  case 'PITCHER_CHANGED': {
    const payload = data;
    options.onPitcherChanged?.(payload);  // ← Callback
    break;
  }
};
```

---

### 5. **MODIFY: `EVENT_SEQUENCES` - Completar todos los eventos**

Los eventos que necesitan secuencias definidas:
- ✅ HOME_RUN
- ✅ STRIKEOUT
- ✅ HIT_1B, HIT_2B, HIT_3B
- ✅ OUT_FLYBALL, OUT_GROUNDBALL
- ✅ BALL, STRIKE
- ✅ PITCHER_CHANGED
- ❌ STEAL (nuevo)
- ❌ DOUBLE_PLAY (nuevo)
- ❌ INNING_COMPLETED (transición)
- ❌ GAME_OVER (fin de juego)

**Acción:** Completar la definición de todas las secuencias basadas en el timing actual

---

### 6. **REMOVE: Efectos y timers redundantes en StadiumShowcaseScreen**

**Eliminar o simplificar:**

```typescript
// ❌ REMOVER: Effect 1 (Effect del lastResult)
// Ya no es necesario porque el hook maneja los timings
useEffect(() => {
  if (lastResult) { ... }
}, [lastResult]);

// ❌ REMOVER: setTimeout en PLAY_RESOLVED del hook
// Ya no es necesario porque usamos EVENT_SEQUENCES
setTimeout(() => { setGameState(...) }, 300);

// ⚠️ MODIFICAR: inningCompleted logic
// Cambiar para que se enquee como evento separado
// o simplemente use el timing de EVENT_SEQUENCES

// ⚠️ MODIFICAR: gameOver logic
// Similar al anterior
```

---

## Flujo Completo después de Implementación

### Antes (Caótico):
```
PLAY_RESOLVED WebSocket event
  ↓
setLastResult() - mostrar overlay
  ↓ (casi inmediato)
setGameState() - actualizar scores, runners, etc. ← Usuario lo ve ANTES del overlay
  ↓ (caótico)
Multiple setState en cascada sin control
  ↓
Usuario confundido: "¿Por qué cambió antes de que lo explicaran?"
```

### Después (Ordenado):
```
PLAY_RESOLVED WebSocket event
  ↓
handlePlayResolved(payload)
  ↓
enqueueEvent('HOME_RUN', payload)
  ↓ (Event Sequencer)
Step 1 (delay: 0ms) - show-modal
  → setLastResult() - Modal visible 3500ms
  ↓ (3600ms)
Step 2 (delay: 3600ms) - update-score
  → setGameState({ homeScore, awayScore })
  ↓ (3700ms)
Step 3 (delay: 3700ms) - update-batter-stats
  → Update stats del bateador
  ↓ (3800ms)
Step 4 (delay: 3800ms) - update-runners
  → Update runners position
  ↓ (4000ms)
Step 5 (delay: 4000ms) - load-next-batter
  → Load nuevo bateador
  ↓
Event completes, next event processes
  ↓
Usuario ve: evento → cambios en orden lógico → siguiente evento
```

---

## Cambios en Componentes Visuales

### PlayResultOverlay.tsx
**Sin cambios necesarios** - Funciona igual, simplemente se mostrará en el momento correcto

### GameOverModal.tsx
**Sin cambios necesarios** - Se mostrará después de que terminen todos los events previos

### CentralField.tsx
**Cambio:** Aceptar prop `disabled`
```typescript
interface CentralFieldProps {
  disabled?: boolean;
}

// En JSX:
<CentralField disabled={isProcessing} />
```

### TacticalHand.tsx
**Cambio:** Aceptar prop `disabled`
```typescript
interface TacticalHandProps {
  disabled?: boolean;
}
```

---

## Testing & Debugging

### Logging del Event Sequencer
```typescript
// Cada evento enqueue
📤 [EVENT QUEUE] Enqueued: HOME_RUN (order: 3)

// Cada evento process
⚙️  [EVENT SEQUENCER] Processing event: HOME_RUN (id: uuid)

// Cada step execute
  📍 [STEP] show-modal (delay: 0ms) - executing callback
  📍 [STEP] update-score (delay: 3600ms) - executing callback

// Evento completado
✅ [EVENT SEQUENCER] Event completed: HOME_RUN
```

### Testing Manual
1. Lanzar pitch → Ver overlay PRIMERO
2. Esperar 3.6s → Ver score actualizado
3. Esperar 0.1s → Ver stats del bateador actualizado
4. Ver que cada cambio está en su momento exacto
5. Queue con múltiples eventos → Cada uno se procesa en orden

---

## Consideraciones de Rendimiento

✅ **Positivas:**
- Un solo `setGameState()` por step (no múltiples)
- Callbacks en JavaScript puro (sin re-renders caóticos)
- Queue permite batching de updates

⚠️ **Potenciales:**
- Si hay muchos eventos en queue, puede haber lag
- Solución: Limitar queue a los últimos 10 eventos (drop oldest si > 10)

---

## Fases de Implementación

### ✅ Fase 1A: Estructura Base del WebSocket (HECHO)
- ✅ Crear `useEventSequencer.ts`
- ✅ Definir `EVENT_SEQUENCES` básicas
- ✅ Modificar `useStadiumSocket` para aceptar callbacks

**Commit:** c4dea28

### 🔄 Fase 1B: Integración en StadiumShowcaseScreen (EN PROGRESO)

**Completado:**
- ✅ Importar `useEventSequencer` y `EVENT_SEQUENCES`
- ✅ Inicializar el hook en el componente
- ✅ Crear handlers para las callbacks del WebSocket
  - ✅ `handlePlayResolved(payload)` → enquee el evento
  - ✅ `handlePitcherChanged(payload)` → enquee el evento
- ✅ Pasar callbacks a `useStadiumSocket`
- ✅ Registrar primer step callback: `show-modal`
- ✅ Agregar estados locales: `lastResult`, `inningCompleted`, `pitcherChanged`

**Commits:**
- 4b8bc66: Hook initialization and WebSocket integration
- 6cd8881: Register 'show-modal' step callback

**Pendiente:**
- [ ] Registrar step callbacks adicionales (update-score, update-stats, etc.)
- [ ] Deshabilitar controles durante evento (`disabled={isProcessing}`)
- [ ] Limpiar effectos redundantes que ya no se necesitan
- [ ] Testear flujo completo de un evento

### 📋 Fase 2: Completar Secuencias (PRÓXIMO)
- Definir todos los `EVENT_SEQUENCES` con timings reales
- Verificar y ajustar delays según UX

### 📋 Fase 3: Testing & Refinamiento (PRÓXIMO)
- Testing manual de cada tipo de evento
- Ajustar timings según feedback

---

## Rollback Plan

Si algo sale mal:
1. Todos los cambios están en features aislados
2. El hook `useEventSequencer` es independiente
3. Si necesario, revertir a los timers simples originales
4. Los estados siguen siendo los mismos, solo se actualizan en orden

---

## Notas Finales

Este sistema es **extensible**: 
- Nuevo tipo de evento? → Solo agregar a `EVENT_SEQUENCES`
- Nuevo step? → Solo agregar a la secuencia
- Cambiar timing? → Solo modificar los `delay` values

Es **mantenible**:
- Toda la lógica en un lugar (EVENT_SEQUENCES)
- Fácil debuggear con logging
- Tests unitarios simples para cada callback

Es **robusto**:
- Handling de errores por step
- Cleanup de timers en unmount
- Prevent race conditions con `processingRef`
