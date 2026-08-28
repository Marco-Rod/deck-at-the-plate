# ✅ Validación de Starter Pack - Checklist Completo

## 🔍 Cómo Validar que Todo Funciona Correctamente

Después de ejecutar el test o abrir el sobre en el frontend, busca en los logs:

---

## ✓ CHECKLIST - Fase 1: Datos Recibidos

### 1. Frontend envía parámetros correctos
```
Busca en logs: [PARAMS] user_id=..., team_id=...
```
- [ ] `user_id` tiene un valor válido (ej: "abc123xyz")
- [ ] `team_id` tiene 2-3 caracteres (ej: "LAD", "NYY")
- [ ] `team_id` está en UPPERCASE

**Si falla:** El frontend no está enviando los datos correctos.

---

## ✓ CHECKLIST - Fase 2: Validación de Usuario

### 2. Usuario existe y tiene club
```
Busca en logs: [VALIDATION] Usuario ... tiene club creado
```
- [ ] No ves error "Debes fundar tu club antes"
- [ ] El usuario tiene `favorite_team_id` registrado

**Si falla:** El usuario no completó la fase de creación de club.

---

## ✓ CHECKLIST - Fase 3: Equipos Disponibles

### 3. Hay cartas del equipo elegido en la BD
```
Busca en logs: [BUSQUEDA] Fielders disponibles en LAD: X
                          Pitchers disponibles en LAD: Y
```
- [ ] `X` es al menos 5 (fielders)
- [ ] `Y` es al menos 2 (pitchers)

**Si falla (X < 5 o Y < 2):** No hay suficientes jugadores en la BD para ese equipo.
- Ejecuta: `python app/seeds/seed_cards.py`

---

## ✓ CHECKLIST - Fase 4: Selección del Equipo Elegido

### 4. Se seleccionaron exactamente 5 fielders + 2 pitchers
```
Busca en logs: [SELECCIONADAS] 5 fielders del equipo elegido
               [SELECCIONADAS] 2 pitchers del equipo elegido
```
- [ ] Ves exactamente "5 fielders"
- [ ] Ves exactamente "2 pitchers"
- [ ] Cada jugador tiene nombre, posición, overall, rareza

**Ejemplo correcto:**
```
  [SELECCIONADAS] 5 fielders del equipo elegido
    1. Mike Trout - Pos: CF - OVR: 99 - Rareza: COMMON
    2. Clayton Kershaw - Pos: SP - OVR: 97 - Rareza: GOLD
    3. Juan Soto - Pos: RF - OVR: 95 - Rareza: SILVER
    4. Francisco Lindor - Pos: SS - OVR: 93 - Rareza: BRONZE
    5. Shohei Ohtani - Pos: DH - OVR: 99 - Rareza: DIAMOND

  [SELECCIONADAS] 2 pitchers del equipo elegido
    1. Gerrit Cole - Pos: SP - OVR: 94 - Rareza: SILVER
    2. Juan Manuel Soto - Pos: RP - OVR: 88 - Rareza: COMMON
```

**Si falla:** La lógica de selección tiene un bug.

---

## ✓ CHECKLIST - Fase 5: Posiciones Cubiertas

### 5. Verifica posiciones requeridas
```
Busca en logs: [POSICIONES_FALTANTES] [lista]
```
- [ ] La lista está vacía `[]`
- [ ] O contiene solo posiciones de pitcher

**Ejemplo correcto:**
```
  [POSICIONES_REQUERIDAS] {'P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF'}
  [POSICIONES_CUBIERTAS] 9
  [POSICIONES_FALTANTES] []  ← ¡Perfecto!
```

**Ejemplo con problema:**
```
  [POSICIONES_CUBIERTAS] 8
  [POSICIONES_FALTANTES] ['1B']  ← Falta primera base
```

---

## ✓ CHECKLIST - Fase 6: Distribución de Rareza

### 6. Valida la distribución esperada (2 SILVER + 4 BRONZE + 7 COMMON)
```
Busca en logs: [PASO 8] RESUMEN FINAL
               [COMPOSICION_POR_RAREZA]
```

**Busca exactamente:**
```
    - SILVER: 2 (esperadas 2) ✓
    - BRONZE: 4 (esperadas 4) ✓
    - COMMON: 7 (esperadas 7) ✓
```

- [ ] `SILVER: 2 ... ✓`
- [ ] `BRONZE: 4 ... ✓`
- [ ] `COMMON: 7 ... ✓`

**Si ves ✗ (cruz) en lugar de ✓:**
```
    - SILVER: 1 (esperadas 2) ✗  ← Hay 1 en lugar de 2
    - BRONZE: 4 (esperadas 4) ✓
    - COMMON: 8 (esperadas 7) ✗  ← Hay 8 en lugar de 7
```

---

## ✓ CHECKLIST - Fase 7: Composición por Equipo

### 7. Valida que 7 cartas sean del equipo elegido
```
Busca en logs: [PASO 8] RESUMEN FINAL
               [COMPOSICION_POR_EQUIPO]
```

**Ejemplo correcto (eligieron LAD):**
```
    - LAD: 7 cartas  ← ¡Correcto! (5 fielders + 2 pitchers)
    - NYY: 2 cartas  ← Otros equipos
    - BOS: 1 cartas
    - SD: 1 cartas
    - CWS: 2 cartas
```

- [ ] El equipo elegido (ej: LAD) tiene exactamente 7 cartas
- [ ] Los otros equipos suman 6 cartas
- [ ] Total es 13

**Si falla (ej: LAD solo tiene 1):**
```
    - LAD: 1 cartas  ← ¡PROBLEMA! Debería ser 7
    - NYY: 3 cartas
    - BOS: 2 cartas
    - ... más equipos
```

---

## ✓ CHECKLIST - Fase 8: Composición por Posición

### 8. Valida que todas las posiciones de campo estén cubiertas
```
Busca en logs: [PASO 8] RESUMEN FINAL
               [COMPOSICION_POR_POSICION]
```

**Ejemplo correcto:**
```
    - 1B: 1  ← Primera base
    - 2B: 1  ← Segunda base
    - 3B: 1  ← Tercera base
    - C: 1   ← Catcher
    - CF: 1  ← Center field
    - LF: 1  ← Left field
    - P: 5   ← Pitcher (múltiples)
    - RF: 1  ← Right field
    - SS: 1  ← Shortstop
```

- [ ] `C: 1` - Catcher ✓
- [ ] `1B: 1` - Primera base ✓
- [ ] `2B: 1` - Segunda base ✓
- [ ] `3B: 1` - Tercera base ✓
- [ ] `SS: 1` - Shortstop ✓
- [ ] `LF: 1` - Left field ✓
- [ ] `CF: 1` - Center field ✓
- [ ] `RF: 1` - Right field ✓
- [ ] `P: X` - Pitcher (al menos 2) ✓

---

## ✓ CHECKLIST - Fase 9: Inventario Guardado

### 9. Valida que todas las cartas se guardaron
```
Busca en logs: [PASO 9] Guardando cartas en inventario del usuario
```

- [ ] Ves 13 líneas de "Guardando: ..."
- [ ] No ves duplicados advertencias (ej: "ya existe en inventario")
- [ ] Log termina con "[COMMIT_SUCCESS]"

**Ejemplo correcto:**
```
  1. Guardando: Mike Trout (LAD) - OVR: 99 - Rareza: DIAMOND
  2. Guardando: Clayton Kershaw (LAD) - OVR: 97 - Rareza: GOLD
  3. Guardando: Juan Soto (LAD) - OVR: 95 - Rareza: SILVER
  ...
  13. Guardando: José Ramirez (CLE) - OVR: 88 - Rareza: COMMON
```

---

## ✓ CHECKLIST - Fase 10: Estado del Usuario

### 10. Valida que el usuario se actualizó
```
Busca en logs: [PASO 10] Actualizando estado del usuario
               [UPDATE] favorite_team_id = LAD
               [UPDATE] has_completed_onboarding = True
```

- [ ] `favorite_team_id` cambió al equipo elegido (LAD)
- [ ] `has_completed_onboarding` es True

---

## ✓ CHECKLIST - Fase 11: Completación

### 11. Verifica que todo terminó exitosamente
```
Busca en logs: [ASSIGN_STARTER_PACK] FIN - 13 cartas asignadas exitosamente
```

- [ ] Ves el mensaje de FIN
- [ ] Dice "13 cartas"

---

## 🎯 Validación Rápida (TL;DR)

Si todo está correcto, deberías ver:

```
[PARAMS] user_id=abc123, team_id=LAD
[VALIDATION] Usuario abc123 tiene club creado
[BUSQUEDA] Fielders disponibles en LAD: 7
[BUSQUEDA] Pitchers disponibles en LAD: 4
[SELECCIONADAS] 5 fielders del equipo elegido
[SELECCIONADAS] 2 pitchers del equipo elegido
[POSICIONES_FALTANTES] []
    - LAD: 7 cartas
    - SILVER: 2 (esperadas 2) ✓
    - BRONZE: 4 (esperadas 4) ✓
    - COMMON: 7 (esperadas 7) ✓
[COMMIT_SUCCESS]
[ASSIGN_STARTER_PACK] FIN - 13 cartas asignadas exitosamente
```

---

## 🐛 Troubleshooting Rápido

| Problema | Busca en Logs | Posible Causa |
|----------|---------------|---------------|
| "Solo 1 carta del equipo" | `[BUSQUEDA] Fielders... LAD: 0` | No hay cartas del equipo en BD |
| "Todas COMMON" | `[OTROS_EQUIPOS] Distribución... SILVER: 0` | Las cartas no tienen rareza correcta |
| "Falta posición 1B" | `[POSICIONES_FALTANTES] ['1B']` | Bug en selección de fielders |
| "Menos de 13 cartas" | `[SUBTOTAL]` o error | No hay suficientes cartas en BD |
| "26 cartas asignadas" | Check duplicados | Problema de inventario duplicado |

---

## 📊 Resumen Visual

```
Frontend                Backend                          BD
   │                       │                              │
   ├─ POST /starter-pack   │                              │
   │  ?user_id=X           │                              │
   │  &team_id=LAD         │                              │
   │                       ├─ [PARAMS] Valida             │
   │                       │                              │
   │                       ├─ [PASO 1] Busca fielders/pitchers ──────┐
   │                       │                              │          │
   │                       │◄─────────────────────────────┘ 7/4
   │                       │
   │                       ├─ [PASO 2-8] Selecciona smartly
   │                       │  • 5 fielders del LAD
   │                       │  • 2 pitchers del LAD
   │                       │  • 2 SILVER otros
   │                       │  • 4 BRONZE otros
   │                       │  • 7 COMMON otros
   │                       │
   │                       ├─ [PASO 9] Guarda 13 cartas ──────────┐
   │                       │                              │         │
   │                       │◄─────────────────────────────┘ INSERT
   │                       │
   │ 200 OK                │
   │ cards: [...]◄─────────┤
   │                       │
```

---

## 🚀 Próximos Pasos

1. **Ejecuta el test o abre sobre en frontend**
2. **Copiar-pega los logs aquí** (o en archivo `logs.txt`)
3. **Llena esta checklist**
4. **Identifica qué paso falla** (si alguno falla)
5. **Reportar el error** con los logs específicos

```bash
# Para guardar logs fácilmente:
# Terminal 1 (Backend)
python -m uvicorn app.main:app --reload 2>&1 | tee backend_logs.txt

# Luego abrir sobre en frontend, y en Terminal 1:
# Ctrl+C para detener

# Buscar en logs:
cat backend_logs.txt | grep "\[PASO"
```
