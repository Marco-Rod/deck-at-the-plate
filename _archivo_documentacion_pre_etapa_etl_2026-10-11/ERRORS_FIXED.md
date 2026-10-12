# Errors Found and Fixed During Testing

## Error #7: ReferenceError: lastResult is not defined

**Ubicación:** `StadiumShowcaseScreen.tsx:411`

**Causa:** Al agregar los callbacks de Event Sequencer, se usó `lastResult` pero no fue inicializado con `useState`.

**Síntoma:**
```
Uncaught ReferenceError: lastResult is not defined
    at StadiumShowcaseScreen (StadiumShowcaseScreen.tsx:411:7)
```

**Solución:**
```typescript
// Agregado después de currentEventPayload
const [lastResult, setLastResult] = useState<{
  text: string;
  event: string;
  ts: number;
} | null>(null);
```

---

## Error #8: ReferenceError: inningCompleted is not defined

**Ubicación:** `StadiumShowcaseScreen.tsx:460` (useEffect que chequea `inningCompleted`)

**Causa:** Se utilizaba `inningCompleted` sin ser extraído de `gameState`. La variable debería derivarse del estado.

**Síntoma:**
```
ReferenceError: inningCompleted is not defined
```

**Solución:**
```typescript
// Agregado como variable derivada
const inningCompleted = gameState?.inning_completed;
```

---

## Error #9: ReferenceError: lastProcessedInningCompletedRef is not defined

**Ubicación:** `StadiumShowcaseScreen.tsx:464` (dentro del useEffect de inningTransition)

**Causa:** Se usaba un `useRef` sin declara rlo.

**Síntoma:**
```
ReferenceError: lastProcessedInningCompletedRef is not defined
```

**Solución:**
```typescript
// Agregado como useRef
const lastProcessedInningCompletedRef = useRef<number | null>(null);
```

---

## Summary

| Error # | Variable | Type | Location | Status |
|---------|----------|------|----------|--------|
| 7 | lastResult | useState | Line 95 | ✅ Fixed |
| 8 | inningCompleted | derived variable | Line 459 | ✅ Fixed |
| 9 | lastProcessedInningCompletedRef | useRef | Line 101 | ✅ Fixed |
| 10 | pitcherChanged | useState | Line 104 | ✅ Fixed |

**Total Errors Fixed: 4**
**All errors were in StadiumShowcaseScreen.tsx**
**Root cause: Missing state/ref declarations when adding Event Sequencer callbacks**

---

## Error #10: ReferenceError: pitcherChanged is not defined

**Ubicación:** `StadiumShowcaseScreen.tsx:818` (useEffect que chequea `pitcherChanged`)

**Causa:** Se usaba `pitcherChanged` en useEffect sin estar declarado. Es un estado que debería actualizarse cuando llega el callback del WebSocket.

**Síntoma:**
```
ReferenceError: pitcherChanged is not defined
    at StadiumShowcaseScreen.tsx:818:7
```

**Solución:**
```typescript
// Agregado como estado
const [pitcherChanged, setPitcherChanged] = useState<any>(null);

// Actualizar handlePitcherChanged para llenar el estado
const handlePitcherChanged = useCallback((payload: any) => {
  console.log(`📤 [HANDLER] Enqueuing PITCHER_CHANGED event`);
  setPitcherChanged(payload);  // ⭐ Actualizar estado local
  enqueueEvent('PITCHER_CHANGED', payload);
}, [enqueueEvent]);
```

