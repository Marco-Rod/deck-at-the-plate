# ⚡ Quick Start - Reset & Validación

## 🔥 Modo Rápido (3 comandos)

```bash
# Terminal 1 - Limpiar + Recargar BD
cd backend
python run_complete_reset.py
# Responde: s

# Terminal 2 - Iniciar Backend
python -m uvicorn app.main:app --reload

# Terminal 3 - Iniciar Frontend
cd ../frontend
npm run dev
```

Luego abre: **http://localhost:5173**

---

## ✅ Validación Rápida (30 segundos)

1. **Crea usuario**: nombre "Test", siglas "TST"
2. **Selecciona equipo**: **NO LAD** (ej: SF, NYY, BOS)
3. **Abre sobre**: 
   - Click en el sobre
   - Espera reveal animado
4. **Verifica en logs** (backend Terminal 2):
   - Busca: `SILVER: 2 (esperadas 2) ✓`
   - Busca: `BRONZE: 4 (esperadas 4) ✓`
   - Busca: `COMMON: 7 (esperadas 7) ✓`
   - Busca: `favorite_team_id asignado a = SF`

✅ **Si ves esto = EXITOSO**

---

## 📋 Checklist de Validación

```
RARITY DISTRIBUTION:
  ☐ Logs muestran 2 SILVER
  ☐ Logs muestran 4 BRONZE
  ☐ Logs muestran 7 COMMON
  ☐ Cards tienen colores diferentes (no todos grises)

TEAM SELECTION:
  ☐ Seleccionas SF (o cualquier otro)
  ☐ Logs muestran SF en [COMPOSICION_POR_EQUIPO] con 7 cartas
  ☐ favorite_team_id = SF (no LAD)

OVERALL VALUES:
  ☐ Cards tienen OVR variados (70s, 80s, 90s)
  ☐ No todas están en 70
```

---

## 🎮 Pasos Detallados si Necesitas

### Paso 1: Limpiar BD

```bash
cd backend
python run_complete_reset.py
```

Output esperado:
```
PASO 1: Limpiando base de datos...
✅ Base de datos limpiada con éxito.
   ✓ Tabla 'users' vaciada
   ✓ Tabla 'teams' vaciada

PASO 2: Cargando datos MLB 2026...
🔄 Iniciando seed de datos MLB 2026...
[1/30] Los Angeles Dodgers
    ✓ Equipo creado
    ✓ 12 lanzadores + 28 bateadores agregados
...
✅ COMPLETADO - Base de datos lista
```

### Paso 2: Backend

```bash
# En carpeta backend/
python -m uvicorn app.main:app --reload
```

Debería ver:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Paso 3: Frontend

```bash
# En carpeta frontend/
npm run dev
```

Debería ver:
```
  ➜  Local:   http://localhost:5173/
  ➜  Press q to quit
```

### Paso 4: Testing

1. Abre: http://localhost:5173
2. Crea usuario (any name/city)
3. **Selecciona equipo distinto a LAD** 
4. Click en "Confirmar y Reclamar Sobre"
5. Click en sobre para abrir
6. Verifica los logs en Terminal del backend

---

## 🔍 Qué Buscar en Logs

### Sección 1: Seed (cuando ejecutas `run_complete_reset.py`)

```
PASO 2: Cargando datos MLB 2026...
🔄 Iniciando seed de datos MLB 2026...
📅 Fecha de datos: 25 de Marzo de 2026

🧹 Limpiando todas las cartas previas...
   ✓ 1200 cartas previas eliminadas

[1/30] 🏟️  Los Angeles Dodgers → Dodgers Ficticios
    ✓ Equipo creado
    ✓ 12 lanzadores + 28 bateadores agregados
[2/30] 🏟️  New York Yankees → Yankees Ficticios
    ✓ Equipo ya existe en BD
    ✓ 13 lanzadores + 27 bateadores agregados
...
✅ Seed completado exitosamente
📊 Resumen: 30 equipos x ~40 jugadores = 1200 jugadores cargados
```

### Sección 2: Pack Assignment (cuando abres el sobre)

```
[ASSIGN_STARTER_PACK] INICIO
[INPUT] user_id=xxxxxxxx, team_id=SF

[PASO 1] Seleccionando jugadores del equipo elegido (SF)
  [BUSQUEDA] Fielders disponibles en SF: 15
  [BUSQUEDA] Pitchers disponibles en SF: 8
  [SELECCIONADAS] 5 fielders del equipo elegido
    1. Player Name - Pos: 2B - OVR: 82 - Rareza: CardRarity.SILVER
    ...

[PASO 8] RESUMEN FINAL - Cartas a guardar (13 total)
  [COMPOSICION_POR_EQUIPO]
    - SF: 7 cartas
    - LAD: 1 cartas
    - NYY: 1 cartas
    - BOS: 1 cartas
    - CWS: 1 cartas
    - OAK: 1 cartas
  [COMPOSICION_POR_RAREZA]
    - DIAMOND: 0 (esperadas 0) ✓
    - GOLD: 0 (esperadas 0) ✓
    - SILVER: 2 (esperadas 2) ✓
    - BRONZE: 4 (esperadas 4) ✓
    - COMMON: 7 (esperadas 7) ✓

[PASO 10] Actualizando estado del usuario
  [UPDATE] favorite_team_id asignado a = SF (no existía)
  [UPDATE] has_completed_onboarding = True

[COMMIT_SUCCESS] Cambios guardados correctamente

[ASSIGN_STARTER_PACK] FIN - 13 cartas asignadas exitosamente
```

**Si ves todo esto = ✅ TODO OK**

---

## ❌ Troubleshooting

### "ModuleNotFoundError: No module named 'requests'"
```bash
pip install requests
python run_complete_reset.py
```

### "connection refused" a BD
```bash
# Verifica que la BD está corriendo
docker ps

# Si no está, inicia con:
docker-compose up -d
```

### Las cartas siguen siendo todas COMMON
```bash
# Verifica logs de seed - ¿Dice "Seed completado"?
# Si no, re-ejecuta:
python run_complete_reset.py

# Luego verifica nuevamente con un usuario nuevo
```

### Frontend sigue mostrando LAD
```bash
# Limpia cache:
# - Chrome/Edge: Ctrl+Shift+Delete
# - Firefox: Ctrl+Shift+Delete  
# - Safari: Cmd+Option+E

# O en Dev Tools (F12):
# - Network tab → Disable cache (checkbox)
# - Recarga: Ctrl+F5 o Cmd+Shift+R
```

---

## 📊 Expected Results

### Console Log (F12 → Console tab)
```
[DEBUG OnboardingScreen] setSelectedFranchise a: SF
[DEBUG] Enviando starter pack con selectedFranchise=SF
```

### Backend Log
```
[SUCCESS] Starter pack asignado: 13 cartas devueltas
```

### UI Cards
- 2 cards con fondo dorado/plateado (SILVER)
- 4 cards con fondo cobre (BRONZE)
- 7 cards con fondo gris/común (COMMON)
- OVR values: 70s, 80s, 90s (variados)

---

## 🎯 Success Criteria

✅ **Completado si**:
1. Seed ejecuta sin errores
2. Cartas tienen rarity 2-4-7
3. OVR values son variados
4. Equipo seleccionado = favorite_team_id (no LAD)
5. 7 cartas del equipo elegido

**Si todo esto pasa = TODOS LOS BUGS ESTÁN FIJOS**

---

## 💾 Guardar Logs

Si necesitas reportar un error:

```bash
# Backend
python -m uvicorn app.main:app --reload 2>&1 | tee backend.log

# Frontend (si hay error)
# Abre DevTools → Console tab → Right-click → Save as...

# Luego comparte los logs para debugging
```

