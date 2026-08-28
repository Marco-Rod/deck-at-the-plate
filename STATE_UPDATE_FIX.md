# Fix: State Updates After Event Modal Display

## Problema
Después de mostrar el modal del evento (ej. HOME_RUN, OUT, STRIKE), los cambios en la interfaz **no se reflejaban**. Los scores, runners y stats se quedaban como estaban.

**Evidencia en consola:**
```
⚠️  [STEP] No callback registered for update-score
⚠️  [STEP] No callback registered for update-batter-stats
⚠️  [STEP] No callback registered for update-runners
⚠️  [STEP] No callback registered for load-next-batter
```

Y los logs del Scoreboard siempre mostraban:
```
🎲 [STADIUM SHOWCASE] Pasando datos al Scoreboard:
   - gameState.inning_runs: {}
   - gameState.homeScore: 0  ← Siempre 0, nunca cambió
   - gameState.awayScore: 0  ← Siempre 0, nunca cambió
```

---

## Causa Raíz

Hay dos problemas:

### Problema 1: gameState nunca se actualiza con los datos del evento
En `useStadiumSocket.ts`, cuando llega `PLAY_RESOLVED`, el código era:

```typescript
case 'PLAY_RESOLVED': {
  const payload = data as PlayResolvedPayload;
  // ⭐ Fase 1 Change: No actualizar state aquí
  // Simplemente notificar al parent para que enquee el evento
  callbacks?.onPlayResolved?.(payload);  // ← Solo callback, no setGameState
  break;
}
```

**El problema:** El evento se enquea en el sequencer, pero el gameState **nunca se actualiza**, así que cuando llega la hora de "update-score", no hay datos nuevos que reflejar.

### Problema 2: No había callbacks implementados para los pasos
En `StadiumShowcaseScreen.tsx`, solo había:
```typescript
useEffect(() => {
  onStep('show-modal', (payload) => { ... });
}, [onStep]);
// Faltaban los demás callbacks
```

---

## Solución Implementada

### Paso 1: Actualizar gameState cuando llega PLAY_RESOLVED
Ahora en `useStadiumSocket.ts`:

```typescript
case 'PLAY_RESOLVED': {
  const payload = data as PlayResolvedPayload;
  console.log('🔵 [FRONTEND] PLAY_RESOLVED received:');
  console.log('   event:', payload.event);
  console.log('   score_home:', payload.score_home);
  console.log('   score_away:', payload.score_away);
  
  // ⭐ NUEVO: Actualizar el gameState con los datos del evento
  setGameState(prevState => {
    if (!prevState) return prevState;
    
    const updatedState = parseStateData({
      ...payload,
      current_inning: payload.current_inning || prevState.currentInning,
      is_top_inning: payload.is_top_inning !== undefined ? payload.is_top_inning : prevState.isTopInning,
      state_data: payload.state_data || prevState.state_data,
      pitcher_strikeouts: payload.pitcher_strikeouts || prevState.pitcher_strikeouts,
      batter_stats: payload.batter_stats || prevState.batter_stats,
    });
    
    console.log('📍 [GAMESTATE UPDATED]:', {
      score_before_home: prevState.homeScore,
      score_after_home: updatedState.homeScore,
      score_before_away: prevState.awayScore,
      score_after_away: updatedState.awayScore,
    });
    
    return updatedState;
  });
  
  // Notificar al parent para que enquee el evento
  callbacks?.onPlayResolved?.(payload);
  break;
}
```

**Qué hace:**
1. Recibe el payload con los datos nuevos del evento
2. Actualiza `gameState` con `parseStateData()`
3. Logs para debugging
4. Notifica al parent para enquear el evento

### Paso 2: Implementar callbacks para los pasos del sequencer
Ahora en `StadiumShowcaseScreen.tsx`:

```typescript
// Callback 1: Show modal at delay 0ms
useEffect(() => {
  onStep('show-modal', (payload) => { ... });
}, [onStep]);

// Callback 2: Update score (después del modal)
useEffect(() => {
  onStep('update-score', (payload) => {
    console.log(`✅ [STEP] update-score - Actualizando scores`);
    console.log('   score_home:', payload.score_home, '| score_away:', payload.score_away);
    // El gameState ya está actualizado por el WebSocket
  });
}, [onStep]);

// Callback 3: Update batter stats
useEffect(() => {
  onStep('update-batter-stats', (payload) => {
    console.log(`✅ [STEP] update-batter-stats - Actualizando estadísticas del bateador`);
    if (payload.batter_stats) {
      console.log('   batter_stats:', payload.batter_stats);
    }
  });
}, [onStep]);

// Callback 4: Update runners
useEffect(() => {
  onStep('update-runners', (payload) => {
    console.log(`✅ [STEP] update-runners - Actualizando corredores`);
    console.log('   runners:', payload.runners || 'N/A');
  });
}, [onStep]);

// Callback 5: Load next batter
useEffect(() => {
  onStep('load-next-batter', (payload) => {
    console.log(`✅ [STEP] load-next-batter - Cargando siguiente bateador`);
    console.log('   active_batter:', payload.active_batter?.name || 'Desconocido');
  });
}, [onStep]);
```

**Qué hace:**
- Registra callbacks para cada paso del sequencer
- Los callbacks loguean que se ejecutaron en el tiempo correcto
- No necesitan hacer mucho porque el `gameState` ya está actualizado por el WebSocket

---

## Flujo Correcto Ahora

```
1. Usuario lanza un pitch
   ↓
2. Backend resuelve la jugada
   ↓
3. WebSocket envía PLAY_RESOLVED con:
   - event: "HOME_RUN"
   - score_home: 1
   - score_away: 0
   - batter_stats: {...}
   - runners: {1b: null, 2b: null, 3b: null}
   - active_batter: {new batter data}
   - ... más datos
   ↓
4. useStadiumSocket recibe PLAY_RESOLVED
   ├─ setGameState() ← ACTUALIZA con datos nuevos
   └─ onPlayResolved() ← Notifica al parent
   ↓
5. StadiumShowcaseScreen enquea el evento en el sequencer
   - HOME_RUN event enqueued
   ↓
6. Event Sequencer comienza a procesar:
   ├─ DELAY 0ms: show-modal
   │  └─ Muestra modal "HOME RUN"
   │  └─ lastResult se actualiza
   ├─ DELAY 3600ms: update-score
   │  └─ Scoreboard se actualiza (gameState.homeScore ya cambió)
   ├─ DELAY 3700ms: update-batter-stats
   │  └─ Stats se actualizan
   ├─ DELAY 3800ms: update-runners
   │  └─ Runners se actualizan
   └─ DELAY 4000ms: load-next-batter
      └─ Nuevo bateador carga (active_batter ya cambió en gameState)
```

---

## Archivos Modificados

| Archivo | Cambio | Línea |
|---------|--------|-------|
| `useStadiumSocket.ts` | Actualizar gameState en PLAY_RESOLVED | ~151 |
| `useStadiumSocket.ts` | Actualizar gameState en STEAL_RESOLVED | ~177 |
| `StadiumShowcaseScreen.tsx` | Añadir callbacks para todos los pasos | ~254-305 |

---

## Verificación

### Qué debería ver en la consola ahora:

1. **Cuando llega un evento:**
```
🔵 [FRONTEND] PLAY_RESOLVED received:
   event: HOME_RUN
   score_home: 1
   score_away: 0

📍 [GAMESTATE UPDATED]:
   score_before_home: 0
   score_after_home: 1
   score_before_away: 0
   score_after_away: 0
```

2. **Cuando el sequencer procesa:**
```
⚙️  [EVENT SEQUENCER] Processing event: HOME_RUN

📍 [STEP] show-modal (delay: 0ms) - executing callback
✅ [STEP] show-modal - Setting PlayResultOverlay

✅ [STEP] update-score - Actualizando scores
   score_home: 1 | score_away: 0

✅ [STEP] update-batter-stats - Actualizando estadísticas...

✅ [STEP] update-runners - Actualizando corredores

✅ [STEP] load-next-batter - Cargando siguiente bateador

✅ [EVENT SEQUENCER] Event completed: HOME_RUN
```

3. **En la interfaz:**
- Modal aparece (delay 0ms)
- Modal desaparece (después ~3500ms)
- **Scoreboard actualiza** (1 carrera para el equipo)
- **Runners actualizan** (si es necesario)
- **Nuevo bateador carga**

---

## Testing

Para verificar que funciona:

1. Lanza un pitch en el juego
2. Mira la consola del navegador
3. Verifica que veas:
   - `🔵 [FRONTEND] PLAY_RESOLVED received`
   - `📍 [GAMESTATE UPDATED]` (los scores cambiaron)
   - Modal del evento
   - Después del modal: cambios en Scoreboard, runners, bateador

---

## Próximos Pasos

1. **Testing manual:** Ejecutar 3-4 pitches y ver si todo se refleja correctamente
2. **Debugging si falla:** Revisar los logs para ver dónde se quedó
3. **Casos especiales:** Probar HOME_RUN, STRIKEOUT, OUT_GROUND para diferentes tipos de eventos
4. **Commit:** Una vez validado, hacer commit de todos los cambios
