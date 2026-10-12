# Event Type Mapping Validation

## Eventos Retornados por Backend

Del análisis de `state_manager.py`, estos son los valores posibles de `final_event`:

1. **STRIKEOUT** - Strike al tercero
2. **WALK** - Base por bolas al cuarto
3. **DOUBLE_PLAY** - Doble play
4. **GAME_OVER** - Juego terminado
5. **STRIKE_LOOKING** - Strike por no swing (del evento original)
6. **STRIKE_SWINGING** - Strike por swing (del evento original)
7. **OUT_GROUND** - Out por roletazo
8. **OUT_FLY** - Out por fly ball
9. **FOUL** - Foul (del evento original)
10. **BALL** - Bola (del evento original)
11. **HIT_1B** - Sencillo (del evento original)
12. **HIT_2B** - Doble (del evento original)
13. **HIT_3B** - Triple (del evento original)
14. **HOME_RUN** - Cuadrangular (del evento original)

---

## Mapeo en EVENT_TYPE_MAP

| Backend Event | Frontend Map | Secuencia | ✅/❌ |
|---------------|--------------|-----------|-------|
| STRIKEOUT | STRIKEOUT | STRIKEOUT | ✅ |
| WALK | WALK | WALK | ✅ |
| DOUBLE_PLAY | DOUBLE_PLAY | DOUBLE_PLAY | ✅ |
| GAME_OVER | (especial) | (especial) | ✅ |
| STRIKE_SWINGING | STRIKE | STRIKE | ✅ |
| STRIKE_LOOKING | STRIKE | STRIKE | ✅ |
| OUT_GROUND | OUT_GROUNDBALL | OUT_GROUNDBALL | ✅ |
| OUT_FLY | OUT_FLYBALL | OUT_FLYBALL | ✅ |
| FOUL | FOUL | FOUL | ✅ |
| BALL | BALL | BALL | ✅ |
| HIT_1B | HIT_1B | HIT_1B | ✅ |
| HIT_2B | HIT_2B | HIT_2B | ✅ |
| HIT_3B | HIT_3B | HIT_3B | ✅ |
| HOME_RUN | HOME_RUN | HOME_RUN | ✅ |

---

## Cobertura Actual

**Total de eventos backend: 14**
**Total de eventos mapeados: 14**
**Cobertura: 100% ✅**

---

## EVENT_TYPE_MAP Completo

```typescript
const EVENT_TYPE_MAP: Record<string, keyof typeof EVENT_SEQUENCES> = {
  // Home Run
  'HOME_RUN': 'HOME_RUN',
  'HOME RUN': 'HOME_RUN',
  
  // Strikeout
  'STRIKEOUT': 'STRIKEOUT',
  'K': 'STRIKEOUT',
  
  // Hits (Singles)
  'HIT_1B': 'HIT_1B',
  '1B': 'HIT_1B',
  'SINGLE': 'HIT_1B',
  
  // Hits (Doubles)
  'HIT_2B': 'HIT_2B',
  '2B': 'HIT_2B',
  'DOUBLE': 'HIT_2B',
  
  // Hits (Triples)
  'HIT_3B': 'HIT_3B',
  '3B': 'HIT_3B',
  'TRIPLE': 'HIT_3B',
  
  // Count
  'BALL': 'BALL',
  'STRIKE': 'STRIKE',
  'STRIKE_SWINGING': 'STRIKE',
  'STRIKE_LOOKING': 'STRIKE',
  
  // Other outcomes
  'FOUL': 'FOUL',
  'WALK': 'WALK',
  'BB': 'WALK',
  
  // Outs
  'OUT_FLYBALL': 'OUT_FLYBALL',
  'OUT_FLY': 'OUT_FLYBALL',
  'FLY': 'OUT_FLYBALL',
  'FLY BALL': 'OUT_FLYBALL',
  
  'OUT_GROUNDBALL': 'OUT_GROUNDBALL',
  'OUT_GROUND': 'OUT_GROUNDBALL',
  'GROUND': 'OUT_GROUNDBALL',
  'GROUND BALL': 'OUT_GROUNDBALL',
  
  // Double Play
  'DOUBLE_PLAY': 'DOUBLE_PLAY',
  'DP': 'DOUBLE_PLAY',
};
```

---

## EVENT_SEQUENCES Definidas

| Secuencia | Display Duration | Steps | ✅ |
|-----------|------------------|-------|-----|
| HOME_RUN | 3500ms | 5 | ✅ |
| STRIKEOUT | 2500ms | 4 | ✅ |
| HIT_1B | 2800ms | 5 | ✅ |
| HIT_2B | 3000ms | 5 | ✅ |
| HIT_3B | 3000ms | 5 | ✅ |
| OUT_FLYBALL | 2400ms | 4 | ✅ |
| OUT_GROUNDBALL | 2400ms | 4 | ✅ |
| BALL | 1800ms | 2 | ✅ |
| STRIKE | 1800ms | 2 | ✅ |
| FOUL | 1800ms | 2 | ✅ |
| WALK | 2400ms | 3 | ✅ |
| DOUBLE_PLAY | 2600ms | 4 | ✅ |
| PITCHER_CHANGED | 2000ms | 3 | ✅ |

**Total: 13 secuencias definidas ✅**

---

## Callbacks Implementados

| Callback | Propósito | Implementado | ✅ |
|----------|-----------|--------------|-----|
| show-modal | Mostrar evento | ✅ | ✅ |
| update-score | Actualizar scores | ✅ | ✅ |
| update-batter-stats | Stats del bateador | ✅ | ✅ |
| update-runners | Corredores | ✅ | ✅ |
| load-next-batter | Siguiente bateador | ✅ | ✅ |
| update-outs | Actualizar outs | ✅ | ✅ |
| update-pitcher-stats | Stats del pitcher | ✅ | ✅ |
| check-inning-end | Verificar fin de entrada | ✅ | ✅ |
| update-strikes | Actualizar strikes | ✅ | ✅ |
| update-balls | Actualizar bolas | ✅ | ✅ |
| update-pitcher-card | Tarjeta del pitcher | ✅ | ✅ |
| reset-pitch-selector | Reset selector | ✅ | ✅ |

**Total: 12 callbacks implementados ✅**

---

## Resumen

✅ **Todos los 14 eventos del backend están mapeados**
✅ **13 secuencias de eventos definidas**
✅ **12 callbacks implementados**
✅ **Cobertura de eventos: 100%**

