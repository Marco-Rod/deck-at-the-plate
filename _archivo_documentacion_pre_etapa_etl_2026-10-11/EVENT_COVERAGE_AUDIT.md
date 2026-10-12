# Event Coverage Audit - Validación de Eventos en Callbacks

## Todos los Eventos Posibles del Backend

Del análisis del código backend (`state_manager.py`, `runner_manager.py`, `stats_recorder.py`), estos son **TODOS** los eventos que pueden retornarse:

### Eventos de At-Bat:

| Evento | Descripción | Cubierto | Callbacks Necesarios |
|--------|------------|----------|---------------------|
| **STRIKE_SWINGING** | Strike por swing | ✅ SÍ (mapeado) | `show-modal` |
| **STRIKE_LOOKING** | Strike por no swing | ✅ SÍ (mapeado) | `show-modal` |
| **BALL** | Bola | ✅ SÍ (mapeado) | `show-modal` |
| **FOUL** | Foul (strike si <2) | ⚠️ NO MAPEADO | `show-modal`, `update-strikes` |
| **WALK** | Base por bolas (4) | ✅ SÍ (mapeado) | `show-modal`, `update-runners`, `load-next-batter` |
| **HIT_1B** | Sencillo | ✅ SÍ (mapeado) | `show-modal`, `update-score`, `update-batter-stats`, `update-runners`, `load-next-batter` |
| **HIT_2B** | Doble | ✅ SÍ (mapeado) | `show-modal`, `update-score`, `update-batter-stats`, `update-runners`, `load-next-batter` |
| **HIT_3B** | Triple | ✅ SÍ (mapeado) | `show-modal`, `update-score`, `update-batter-stats`, `update-runners`, `load-next-batter` |
| **HOME_RUN** | Cuadrangular | ✅ SÍ (mapeado) | `show-modal`, `update-score`, `update-batter-stats`, `update-runners`, `load-next-batter` |
| **OUT_FLY** | Out por fly ball | ✅ SÍ (mapeado) | `show-modal`, `update-outs` |
| **OUT_GROUND** | Out por roletazo | ✅ SÍ (mapeado) | `show-modal`, `update-outs` |
| **DOUBLE_PLAY** | Doble play | ✅ SÍ (mapeado) | `show-modal`, `update-outs`, `update-runners` |
| **STRIKEOUT** | Strikeout (3 strikes) | ✅ SÍ (mapeado) | `show-modal`, `update-outs`, `update-pitcher-stats` |
| **GAME_OVER** | Juego terminado | ✅ SÍ (especial) | N/A (manejo especial) |

---

## Mapeo Actual en Frontend (EVENT_TYPE_MAP)

```typescript
const EVENT_TYPE_MAP: Record<string, keyof typeof EVENT_SEQUENCES> = {
  'HOME_RUN': 'HOME_RUN',
  'HOME RUN': 'HOME_RUN',
  'STRIKEOUT': 'STRIKEOUT',
  'K': 'STRIKEOUT',
  'HIT_1B': 'HIT_1B',
  '1B': 'HIT_1B',
  'SINGLE': 'HIT_1B',
  'HIT_2B': 'HIT_2B',
  '2B': 'HIT_2B',
  'DOUBLE': 'HIT_2B',
  'HIT_3B': 'HIT_3B',
  '3B': 'HIT_3B',
  'TRIPLE': 'HIT_3B',
  'BALL': 'BALL',
  'STRIKE': 'STRIKE',  // ← Genérico para STRIKE_SWINGING y STRIKE_LOOKING
  'OUT_FLYBALL': 'OUT_FLYBALL',
  'FLY': 'OUT_FLYBALL',
  'FLY BALL': 'OUT_FLYBALL',
  'OUT_GROUNDBALL': 'OUT_GROUNDBALL',
  'GROUND': 'OUT_GROUNDBALL',
  'GROUND BALL': 'OUT_GROUNDBALL',
};
```

---

## Secuencias de Eventos Definidas (EVENT_SEQUENCES)

```typescript
export const EVENT_SEQUENCES = {
  HOME_RUN: {
    displayDuration: 3500,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-score', delay: 3600 },
      { name: 'update-batter-stats', delay: 3700 },
      { name: 'update-runners', delay: 3800 },
      { name: 'load-next-batter', delay: 4000 },
    ],
  },
  STRIKEOUT: {
    displayDuration: 2500,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-outs', delay: 2600 },         // ⚠️ SIN CALLBACK
      { name: 'update-pitcher-stats', delay: 2700 }, // ⚠️ SIN CALLBACK
      { name: 'check-inning-end', delay: 2800 },    // ⚠️ SIN CALLBACK
    ],
  },
  HIT_1B: {
    displayDuration: 2800,
    steps: [
      { name: 'show-modal', delay: 0 },
      { name: 'update-score', delay: 2900 },
      { name: 'update-batter-stats', delay: 3000 },
      { name: 'update-runners', delay: 3100 },
      { name: 'load-next-batter', delay: 3200 },
    ],
  },
  // ... más eventos
};
```

---

## Callbacks Registrados Actualmente

✅ `show-modal` - Mostrar el evento  
✅ `update-score` - Actualizar scores  
✅ `update-batter-stats` - Actualizar stats del bateador  
✅ `update-runners` - Actualizar corredores  
✅ `load-next-batter` - Cargar siguiente bateador  

❌ `update-outs` - **NO IMPLEMENTADO**  
❌ `update-pitcher-stats` - **NO IMPLEMENTADO**  
❌ `check-inning-end` - **NO IMPLEMENTADO**  
❌ `update-strikes` - **NO IMPLEMENTADO**  

---

## Problemas Identificados

### 1. ⚠️ Eventos sin Mapeo:

- **FOUL** - No tiene secuencia definida. Necesita:
  - Secuencia: `HIT_1B` temporal (no es ideal, debería tener su propia)
  - Steps: `show-modal`, `update-strikes`

- **STRIKE_SWINGING** y **STRIKE_LOOKING** - Se mapean a "STRIKE" genérico
  - Debería mantener `STRIKE` como secuencia genérica ✅

- **BALL** - Mapeado pero no tiene secuencia en EVENT_SEQUENCES
  - Necesita: secuencia `BALL` con `show-modal`, `update-balls`

### 2. ❌ Callbacks Faltantes en Implementación:

```
⚠️  [STEP] No callback registered for update-outs
⚠️  [STEP] No callback registered for update-pitcher-stats
⚠️  [STEP] No callback registered for check-inning-end
```

Estos callbacks existen en EVENT_SEQUENCES pero **no tienen implementación** en StadiumShowcaseScreen.

### 3. ⚠️ Eventos sin Secuencia Definida:

- `FOUL` - Debería tener su propia secuencia
- `BALL` - Solo tiene mapeo, no tiene secuencia
- `STRIKE` - Solo tiene mapeo, no tiene secuencia
- `DOUBLE_PLAY` - No tiene secuencia definida

---

## Plan de Corrección

### Paso 1: Definir Secuencias Faltantes en EVENT_SEQUENCES

```typescript
STRIKE: {
  displayDuration: 1500,
  steps: [
    { name: 'show-modal', delay: 0 },
    { name: 'update-strikes', delay: 1600 },
  ],
},

BALL: {
  displayDuration: 1500,
  steps: [
    { name: 'show-modal', delay: 0 },
    { name: 'update-balls', delay: 1600 },
  ],
},

FOUL: {
  displayDuration: 1800,
  steps: [
    { name: 'show-modal', delay: 0 },
    { name: 'update-strikes', delay: 1900 },
  ],
},

OUT_FLYBALL: {
  displayDuration: 2400,
  steps: [
    { name: 'show-modal', delay: 0 },
    { name: 'update-outs', delay: 2500 },
    { name: 'check-inning-end', delay: 2600 },
  ],
},

OUT_GROUNDBALL: {
  displayDuration: 2400,
  steps: [
    { name: 'show-modal', delay: 0 },
    { name: 'update-outs', delay: 2500 },
    { name: 'check-inning-end', delay: 2600 },
  ],
},

DOUBLE_PLAY: {
  displayDuration: 2600,
  steps: [
    { name: 'show-modal', delay: 0 },
    { name: 'update-outs', delay: 2700 },
    { name: 'update-runners', delay: 2800 },
    { name: 'check-inning-end', delay: 2900 },
  ],
},
```

### Paso 2: Implementar Callbacks Faltantes en StadiumShowcaseScreen

```typescript
// update-outs
onStep('update-outs', (payload) => {
  console.log(`✅ [STEP] update-outs - Actualizando outs`);
  console.log('   outs:', payload.outs);
});

// update-pitcher-stats
onStep('update-pitcher-stats', (payload) => {
  console.log(`✅ [STEP] update-pitcher-stats`);
});

// update-strikes
onStep('update-strikes', (payload) => {
  console.log(`✅ [STEP] update-strikes - Actualizando strikes`);
  console.log('   strikes:', payload.strikes);
});

// update-balls
onStep('update-balls', (payload) => {
  console.log(`✅ [STEP] update-balls - Actualizando bolas`);
  console.log('   balls:', payload.balls);
});

// check-inning-end
onStep('check-inning-end', (payload) => {
  console.log(`✅ [STEP] check-inning-end - Verificar fin de entrada`);
});
```

### Paso 3: Actualizar EVENT_TYPE_MAP si es necesario

Agregar mapeos para variantes de nombres que el backend pueda enviar:
- `WALK` → `WALK`
- `FOUL` → `FOUL`
- `DOUBLE_PLAY` → `DOUBLE_PLAY`
- `OUT_FLYBALL` → `OUT_FLYBALL`
- `OUT_GROUNDBALL` → `OUT_GROUNDBALL`
- `BALL` → `BALL`
- `STRIKE_SWINGING` → `STRIKE`
- `STRIKE_LOOKING` → `STRIKE`

---

## Verificación Rápida

**¿Cuántos eventos únicos retorna el backend?**
- STRIKE_SWINGING, STRIKE_LOOKING, BALL, FOUL, WALK
- HIT_1B, HIT_2B, HIT_3B, HOME_RUN
- OUT_FLY, OUT_GROUND
- DOUBLE_PLAY, STRIKEOUT
- GAME_OVER

**Total: 14 eventos diferentes**

**¿Cuántos tienen secuencia definida actualmente?**
- HOME_RUN, STRIKEOUT, HIT_1B, HIT_2B, HIT_3B, OUT_FLYBALL, OUT_GROUNDBALL, BALL (?), STRIKE (?)

**Faltan secuencias:** FOUL, DOUBLE_PLAY, WALK (parcial), STRIKE (no definido), BALL (no definido)

---

## Resumen de Acciones Necesarias

| Acción | Prioridad | Esfuerzo |
|--------|-----------|----------|
| Definir EVENT_SEQUENCES para FOUL, BALL, STRIKE, DOUBLE_PLAY | ALTA | Bajo |
| Implementar callbacks: update-outs, update-pitcher-stats, check-inning-end, update-strikes, update-balls | ALTA | Bajo |
| Validar EVENT_TYPE_MAP tenga todos los eventos | MEDIA | Bajo |
| Pruebas con cada evento para confirmar funcionamiento | MEDIA | Medio |

