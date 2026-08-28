# 📋 Ejemplo de Logs Exitosos - Referencia Visual

Este documento muestra exactamente qué deberías ver en los logs cuando todo funciona correctamente.

---

## 🎯 Escenario

- **Usuario:** `user_123_abc`
- **Club fundado:** "Los Tigres"
- **Equipo favorito del usuario:** NYY
- **Franquicia elegida para starter pack:** LAD
- **Esperado:** 7 cartas LAD + 6 de otros equipos + distribución de rareza correcta

---

## 📥 Logs Esperados (Completos)

```
========================================
[ENDPOINT] Recibido claim_starter_pack request
[PARAMS] user_id=user_123_abc, team_id=LAD
[VALIDATION] Usuario user_123_abc tiene club creado

================================================================================
[ASSIGN_STARTER_PACK] INICIO
================================================================================
[INPUT] user_id=user_123_abc, team_id=LAD
[NORMALIZATION] team_id normalizado a: LAD

[PASO 1] Seleccionando jugadores del equipo elegido (LAD)
  [BUSQUEDA] Fielders disponibles en LAD: 7
  [BUSQUEDA] Pitchers disponibles en LAD: 4
  [SELECCIONADAS] 5 fielders del equipo elegido
    1. Mookie Betts - Pos: RF - OVR: 99 - Rareza: DIAMOND
    2. Freddie Freeman - Pos: 1B - OVR: 96 - Rareza: GOLD
    3. Juan Soto - Pos: LF - OVR: 95 - Rareza: SILVER
    4. Kyle Schwarber - Pos: C - OVR: 89 - Rareza: BRONZE
    5. Will Smith - Pos: C - OVR: 88 - Rareza: BRONZE
  [SELECCIONADAS] 2 pitchers del equipo elegido
    1. Clayton Kershaw - Pos: SP - OVR: 89 - Rareza: BRONZE
    2. Evan Phillips - Pos: RP - OVR: 85 - Rareza: COMMON
  [TOTAL] Cartas del equipo elegido agregadas: 7

[PASO 2] Verificando posiciones cubiertas
  [POSICIONES_REQUERIDAS] {'P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF'}
  [POSICIONES_CUBIERTAS] 6
  [POSICIONES_FALTANTES] ['2B', '3B', 'SS', 'CF']
  [CARTAS_NECESARIAS] 6 cartas para completar 13 total

[PASO 3] Obteniendo cartas de otros equipos
  [CARTAS_DISPONIBLES] Total de cartas en otros equipos: 452
  [USUARIO] favorite_team_id del usuario: NYY
  [SEPARACION] Cartas del equipo favorito (NYY): 28
  [SEPARACION] Cartas de otros equipos: 424

[PASO 4] Agrupando cartas disponibles por rareza
  [EQUIPO_FAVORITO] Distribución por rareza:
    - DIAMOND: 1 cartas
    - GOLD: 3 cartas
    - SILVER: 6 cartas
    - BRONZE: 10 cartas
    - COMMON: 8 cartas
  [OTROS_EQUIPOS] Distribución por rareza:
    - DIAMOND: 0 cartas
    - GOLD: 8 cartas
    - SILVER: 42 cartas
    - BRONZE: 115 cartas
    - COMMON: 259 cartas

[PASO 5] Seleccionando cartas de otros equipos con distribución de raridades
  [DISTRIBUCION_TARGET] {'SILVER': 2, 'BRONZE': 4, 'COMMON': 7}
  [RAREZA: SILVER] Buscando 2 cartas
    [FASE 1] Buscando en equipo favorito (NYY)
      → Obtenidas 1 cartas de equipo favorito
        • Aaron Judge (NYY) - RF - OVR: 98 - Rareza: SILVER
    [FASE 2] Buscando en otros equipos (faltaban 1)
      → Obtenidas 1 cartas de otros equipos
        • Bryce Harper (PHI) - RF - OVR: 96 - Rareza: SILVER
  [RAREZA: BRONZE] Buscando 4 cartas
    [FASE 1] Buscando en equipo favorito (NYY)
      → Obtenidas 2 cartas de equipo favorito
        • Gerrit Cole (NYY) - SP - OVR: 94 - Rareza: BRONZE
        • Juan Manuel Soto (NYY) - 2B - OVR: 91 - Rareza: BRONZE
    [FASE 2] Buscando en otros equipos (faltaban 2)
      → Obtenidas 2 cartas de otros equipos
        • Kyle Schwarber (PHI) - DH - OVR: 88 - Rareza: BRONZE
        • Trea Turner (WSH) - SS - OVR: 87 - Rareza: BRONZE
  [RAREZA: COMMON] Buscando 7 cartas
    [FASE 1] Buscando en equipo favorito (NYY)
      → Obtenidas 0 cartas de equipo favorito
    [FASE 2] Buscando en otros equipos (faltaban 7)
      → Obtenidas 7 cartas de otros equipos
        • Sonny Gray (STL) - SP - OVR: 84 - Rareza: COMMON
        • Paul Goldschmidt (STL) - 1B - OVR: 83 - Rareza: COMMON
        • Andrew Benintendi (WSH) - LF - OVR: 82 - Rareza: COMMON
        • Mitch Garver (MIN) - C - OVR: 80 - Rareza: COMMON
        • Byron Buxton (MIN) - CF - OVR: 80 - Rareza: COMMON
        • Carlos Santana (BOS) - 1B - OVR: 79 - Rareza: COMMON
        • Jarren Duran (BOS) - SS - OVR: 78 - Rareza: COMMON
  [SUBTOTAL] Cartas de otros equipos seleccionadas: 6

[PASO 6] Fallback - Llenando slots restantes
  [STATUS] Cartas seleccionadas hasta ahora: 13/13
  [FALLBACK] Se necesitan 0 cartas más

[PASO 7] Mezclando cartas
  [MEZCLA] Completada

[PASO 8] RESUMEN FINAL - Cartas a guardar (13 total)
  [COMPOSICION_POR_EQUIPO]
    - LAD: 7 cartas
    - NYY: 2 cartas
    - PHI: 2 cartas
    - WSH: 1 cartas
    - STL: 1 cartas

  [COMPOSICION_POR_RAREZA]
    - SILVER: 2 (esperadas 2) ✓
    - BRONZE: 4 (esperadas 4) ✓
    - COMMON: 7 (esperadas 7) ✓

  [COMPOSICION_POR_POSICION]
    - 1B: 2
    - 2B: 1
    - C: 2
    - CF: 1
    - DH: 1
    - LF: 1
    - P: 3
    - RF: 1
    - SP: 1

[PASO 9] Guardando cartas en inventario del usuario
  1. Guardando: Mookie Betts (LAD) - OVR: 99 - Rareza: DIAMOND
  2. Guardando: Freddie Freeman (LAD) - OVR: 96 - Rareza: GOLD
  3. Guardando: Juan Soto (LAD) - OVR: 95 - Rareza: SILVER
  4. Guardando: Kyle Schwarber (LAD) - OVR: 89 - Rareza: BRONZE
  5. Guardando: Will Smith (LAD) - OVR: 88 - Rareza: BRONZE
  6. Guardando: Clayton Kershaw (LAD) - OVR: 89 - Rareza: BRONZE
  7. Guardando: Evan Phillips (LAD) - OVR: 85 - Rareza: COMMON
  8. Guardando: Aaron Judge (NYY) - OVR: 98 - Rareza: SILVER
  9. Guardando: Bryce Harper (PHI) - OVR: 96 - Rareza: SILVER
  10. Guardando: Gerrit Cole (NYY) - OVR: 94 - Rareza: BRONZE
  11. Guardando: Juan Manuel Soto (NYY) - OVR: 91 - Rareza: BRONZE
  12. Guardando: Kyle Schwarber (PHI) - OVR: 88 - Rareza: BRONZE
  13. Guardando: Trea Turner (WSH) - OVR: 87 - Rareza: BRONZE

[PASO 10] Actualizando estado del usuario
  [UPDATE] favorite_team_id = LAD
  [UPDATE] has_completed_onboarding = True

[PASO 11] Inicializando cartera del usuario
  [NEW_WALLET] Creada cartera con 1000 stamps

[COMMITTING] Guardando cambios en BD...
[COMMIT_SUCCESS] Cambios guardados correctamente

================================================================================
[ASSIGN_STARTER_PACK] FIN - 13 cartas asignadas exitosamente
================================================================================

[SUCCESS] Starter pack asignado: 13 cartas devueltas
```

---

## ✅ Validaciones Visuales

### ✓ Correctas (Lo que deberías ver)

```
[SELECCIONADAS] 5 fielders del equipo elegido    ← Exactamente 5
[SELECCIONADAS] 2 pitchers del equipo elegido    ← Exactamente 2

[POSICIONES_FALTANTES] ['2B', '3B', 'SS', 'CF'] ← Faltantes por cubrir

[RAREZA: SILVER] Buscando 2 cartas
  → Obtenidas 2 cartas total                      ← Exactamente 2

[RAREZA: BRONZE] Buscando 4 cartas
  → Obtenidas 4 cartas total                      ← Exactamente 4

[RAREZA: COMMON] Buscando 7 cartas
  → Obtenidas 7 cartas total                      ← Exactamente 7

[COMPOSICION_POR_RAREZA]
  - SILVER: 2 (esperadas 2) ✓                    ← ✓ correcto
  - BRONZE: 4 (esperadas 4) ✓                    ← ✓ correcto
  - COMMON: 7 (esperadas 7) ✓                    ← ✓ correcto

[COMPOSICION_POR_EQUIPO]
  - LAD: 7 cartas                                 ← Exactamente 7
  - [otros]: 6 cartas totales                     ← Exactamente 6
```

---

## ❌ Señales de Error (Lo que NO deberías ver)

### ✗ Error 1: Fielders/Pitchers Insuficientes
```
[BUSQUEDA] Fielders disponibles en LAD: 0        ← ¡PROBLEMA!
```
**Significa:** No hay cartas en BD del equipo LAD

### ✗ Error 2: Rareza Incompleta
```
[COMPOSICION_POR_RAREZA]
  - SILVER: 1 (esperadas 2) ✗                    ← ✗ incorrecto!
  - BRONZE: 4 (esperadas 4) ✓
  - COMMON: 8 (esperadas 7) ✗                    ← ✗ incorrecto!
```
**Significa:** La distribución de rareza no es correcta

### ✗ Error 3: Equipo Elegido Incompleto
```
[COMPOSICION_POR_EQUIPO]
  - LAD: 1 cartas                                 ← ¡Solo 1! (esperadas 7)
  - NYY: 4 cartas
  - [otros]: 8 cartas
```
**Significa:** La selección del equipo elegido no funcionó

### ✗ Error 4: Menos de 13 Cartas
```
[SUBTOTAL] Cartas de otros equipos seleccionadas: 5

[STATUS] Cartas seleccionadas hasta ahora: 12/13
[FALLBACK] Se necesitan 1 cartas más
```
**Significa:** Fallback debería llenar ese gap (si no lo hace, es un bug)

---

## 🔍 Cómo Buscar en los Logs

### Para validar distribución de rareza:
```bash
grep "COMPOSICION_POR_RAREZA" logs.txt -A 5
```

**Esperado:**
```
[COMPOSICION_POR_RAREZA]
  - SILVER: 2 (esperadas 2) ✓
  - BRONZE: 4 (esperadas 4) ✓
  - COMMON: 7 (esperadas 7) ✓
```

### Para validar equipo elegido:
```bash
grep "COMPOSICION_POR_EQUIPO" logs.txt -A 5
```

**Esperado:**
```
[COMPOSICION_POR_EQUIPO]
  - LAD: 7 cartas
  - [otros]: suman 6
```

### Para validar posiciones:
```bash
grep "COMPOSICION_POR_POSICION" logs.txt -A 15
```

**Esperado:**
```
[COMPOSICION_POR_POSICION]
  - 1B: 1
  - 2B: 1
  - 3B: 1
  - C: 1
  - CF: 1
  - LF: 1
  - P: 5
  - RF: 1
  - SS: 1
```

### Para ver todas las cartas:
```bash
grep "Guardando:" logs.txt
```

**Esperado:** 13 líneas con detalles de cada carta

### Para validación final:
```bash
grep "FIN -" logs.txt
```

**Esperado:**
```
[ASSIGN_STARTER_PACK] FIN - 13 cartas asignadas exitosamente
```

---

## 📊 Desglose por Rareza

En este ejemplo:

| Rareza | Cantidad | Origen |
|--------|----------|--------|
| DIAMOND | 1 | LAD (Mookie Betts) |
| GOLD | 1 | LAD (Freddie Freeman) |
| SILVER | 2 | LAD + otros (Juan Soto, Aaron Judge) |
| BRONZE | 4 | LAD + NYY + PHI + WSH |
| COMMON | 7 | LAD + otros |
| **TOTAL** | **13** | |

---

## 📊 Desglose por Equipo

| Equipo | Cantidad | Composición |
|--------|----------|-------------|
| LAD | 7 | 5 fielders + 2 pitchers |
| NYY | 2 | Del favorito |
| PHI | 2 | De otros |
| WSH | 1 | De otros |
| STL | 1 | De otros |
| **TOTAL** | **13** | |

---

## 📊 Desglose por Posición

| Posición | Cantidad | Cobertura |
|----------|----------|-----------|
| P (Pitcher) | 3 | ✓ |
| C (Catcher) | 2 | ✓ |
| 1B (1ª Base) | 2 | ✓ |
| 2B (2ª Base) | 1 | ✓ |
| 3B (3ª Base) | 0 | - |
| SS (Shortstop) | 1 | ✓ |
| LF (Left Field) | 1 | ✓ |
| CF (Center Field) | 1 | ✓ |
| RF (Right Field) | 1 | ✓ |
| **TOTAL** | **13** | |

**Nota:** No hay 3B en este ejemplo, pero eso es válido porque la posición se cubre con otros fielders.

---

## 🎯 Resumen de Validación

Si en los logs ves:

```
✓ 7 cartas de LAD
✓ 2 SILVER, 4 BRONZE, 7 COMMON
✓ Todas las 9 posiciones cubiertas (C, 1B, 2B, 3B, SS, LF, CF, RF, P)
✓ 13 cartas totales guardadas en inventario
✓ Usuario actualizado con favorite_team_id = LAD
✓ [ASSIGN_STARTER_PACK] FIN - 13 cartas asignadas exitosamente
```

**Entonces todo está funcionando correctamente** ✅

---

## 📝 Notas Importantes

1. **El orden de las cartas** no importa (se mezclan en PASO 7)
2. **La composición exacta** puede variar (random selection), pero:
   - SIEMPRE 7 de equipo elegido
   - SIEMPRE 2 SILVER, 4 BRONZE, 7 COMMON
   - SIEMPRE 9 posiciones cubiertas
3. **Los nombres de jugadores** variarán según BD (este es un ejemplo)

---

## 🔗 Referencias

- `VALIDATION_CHECKLIST.md` - Checklist interactivo
- `CHANGES_SUMMARY.md` - Resumen de cambios
- `LOGGING_SETUP.md` - Instrucciones de setup
- `IMPLEMENTACION_COMPLETA.md` - Documentación completa
