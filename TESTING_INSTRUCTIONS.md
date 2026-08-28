# 🧪 Instrucciones para Validar Fixes de Pack Assignment

## Resumen de Bugs Corregidos

### Bug #1: Distribución de rareza incorrecta
- **Problema**: Todas las cartas COMMON (0 SILVER, 0 BRONZE, 13 COMMON en lugar de 2-4-7)
- **Causa**: 
  - seed_mlb_2026.py verificaba "primaryNumber" pero guardaba "jerseyNumber" → todos overall=70
  - Rarity mapping incompleto (solo COMMON/BRONZE/SILVER, sin GOLD/DIAMOND)
- **Correcciones**:
  - ✅ Línea 287: Cambié verificación a "jerseyNumber"
  - ✅ Línea 319: Agregué mapeo completo DIAMOND(90+)/GOLD(85+)/SILVER(80+)/BRONZE(75+)/COMMON

### Bug #2: Equipo favorito no respetado
- **Problema**: Frontend enviaba LAD en lugar del equipo seleccionado (SF, PIT, etc)
- **Causa**:
  - OnboardingScreen.jsx inicializaba selectedFranchise='LAD' hardcodeado
  - pack_service.py sobrescribía favorite_team_id con el team_id del pack
- **Correcciones**:
  - ✅ OnboardingScreen.jsx línea 59: Cambié a `useState('')`
  - ✅ OnboardingScreen.jsx líneas 97-101: Agregué fallback para asegurar equipo seleccionado
  - ✅ pack_service.py líneas 457-460: Modificada lógica para NO sobrescribir favorite_team_id existente

---

## 📋 Pasos para Validar

### Opción A: Reset Completo (Recomendado para dev)

```bash
# Terminal 1: Limpiar BD y recargar datos
cd backend
python run_complete_reset.py

# Cuando se pida confirmación, escribe: s

# Debería ver output similar a:
# ✅ Base de datos limpiada con éxito.
# ✅ Seed completado exitosamente
# ✓ Todos los usuarios eliminados
# ✓ Todos los equipos recreados de 0
# ✓ ~1200 cartas cargadas con fixes
```

### Opción B: Reset Manual (Por pasos)

```bash
# Terminal 1: Limpiar base de datos
cd backend
python app/seeds/clean_db.py
# Confirma con: s

# Terminal 2: Cargar datos MLB 2026 (solo si está disponible pip)
python app/seeds/seed_mlb_2026.py
```

### Paso 2: Iniciar Backend

```bash
# Terminal (en backend/)
python -m uvicorn app.main:app --reload
# Debería ver: Uvicorn running on http://127.0.0.1:8000
```

### Paso 3: Iniciar Frontend

```bash
# Terminal (en frontend/)
npm run dev
# Debería ver: ➜ Local: http://localhost:5173/
```

### Paso 4: Testing en Browser

1. **Abre**: http://localhost:5173
2. **Crea un nuevo usuario**:
   - Nombre de club: "Test Club"
   - Siglas: "TST"
   - Otros campos: valores por defecto

3. **En la pantalla de selección de franquicia**:
   - **IMPORTANTE**: Selecciona un equipo distinto a LAD
   - Ejemplos: SF (Giants), NYY (Yankees), BOS (Red Sox), etc.
   - Verifica en la consola (F12) que muestre: `[DEBUG OnboardingScreen] setSelectedFranchise a: SF`

4. **Abre el sobre inicial**:
   - Haz clic en "Confirmar y Reclamar Sobre"
   - Se abrirá una animación
   - Haz clic en el sobre para revelar las cartas

5. **Verifica los Logs** (en Terminal del backend):
   - Busca sección `[COMPOSICION_POR_RAREZA]`:
     ```
     - DIAMOND: X (esperadas 0) ✓
     - GOLD: X (esperadas 0) ✓
     - SILVER: 2 (esperadas 2) ✓
     - BRONZE: 4 (esperadas 4) ✓
     - COMMON: 7 (esperadas 7) ✓
     ```
   - Busca sección `[COMPOSICION_POR_EQUIPO]`:
     ```
     - SF: 7 cartas (team_id seleccionado)
     - (otros equipos): 1-2 cartas cada uno
     ```
   - Busca sección `[UPDATE]`:
     ```
     [UPDATE] favorite_team_id asignado a = SF (no existía)
     ```

6. **Verifica en la UI**:
   - Las cartas mostradas deben tener rarity correcta:
     - 2 cartas con fondo dorado/plateado (SILVER)
     - 4 cartas con fondo cobre/bronce (BRONZE)
     - 7 cartas con fondo gris/común (COMMON)
   - Los valores OVR deben variar: algunos 70s, 80s, 90s (no todos 70)
   - Al hacer clic en una carta, verifica "RAREZA" en el modal

---

## ✅ Criterios de Éxito

### Bug #1 - Rarity Distribution
- [ ] Logs muestran SILVER: 2, BRONZE: 4, COMMON: 7
- [ ] Cards en UI reflejan rareza visualmente (colores diferentes)
- [ ] OVR values son variados (no todos 70)

### Bug #2 - Team Selection
- [ ] Seleccionas SF (u otro) → logs muestran SF en [COMPOSICION_POR_EQUIPO]
- [ ] favorite_team_id en logs = SF (no LAD)
- [ ] 7 cartas del equipo seleccionado, 6 de otros
- [ ] Console log (F12) muestra `[DEBUG] setSelectedFranchise a: SF`

### General
- [ ] Sin errores en consola (frontend) excepto warnings normales
- [ ] Sin errores en logs (backend) excepto INFO
- [ ] Página carga sin freezes
- [ ] Sobre se abre correctamente

---

## 🐛 Si Hay Errores

### Error: "ModuleNotFoundError: No module named 'requests'"
```bash
# En backend/
pip install -r requirements.txt
python run_complete_reset.py
```

### Error: "database connection refused"
- Verifica que PostgreSQL está corriendo: `docker ps`
- Si no: `docker-compose up -d` (si tienes docker-compose.yml)

### Las cartas aún muestran todas COMMON
- Verifica que seed_mlb_2026.py ejecutó sin errores
- Busca en logs: `✅ Seed completado exitosamente`
- Intenta ejecutar nuevamente

### Frontend sigue enviando LAD
- Limpia cache: Ctrl+Shift+Delete o Cmd+Shift+Delete
- Abre dev tools (F12), tab Network, desactiva caché
- Recarga: Ctrl+F5 o Cmd+Shift+R
- Verifica que OnboardingScreen.jsx línea 59 tiene `useState('')`

---

## 📊 Expected Output

### Backend Logs (seed)
```
🔄 Iniciando seed de datos MLB 2026...
📅 Fecha de datos: 25 de Marzo de 2026

🧹 Limpiando todas las cartas previas...
   ✓ 0 referencias de inventario eliminadas
   ✓ 1200 cartas previas eliminadas

📥 Obteniendo equipos de MLB...
✓ Se obtuvieron 30 equipos
[1/30] 🏟️  Los Angeles Dodgers → Dodgers Ficticios
    ✓ Equipo creado
    📋 Obteniendo roster de 40 jugadores...
    ✓ 40 jugadores encontrados
    ✓ 12 lanzadores + 28 bateadores agregados
[2/30] 🏟️  New York Yankees → Yankees Ficticios
    ...
✅ Seed completado exitosamente
📊 Resumen: 30 equipos x ~40 jugadores = 1200 jugadores cargados
```

### Backend Logs (pack assignment)
```
[PASO 8] RESUMEN FINAL - Cartas a guardar (13 total)
  [COMPOSICION_POR_EQUIPO]
    - SF: 7 cartas
    - LAD: 1 cartas
    - NYY: 1 cartas
    - BOS: 1 cartas
    - ATL: 1 cartas
    - MIN: 1 carta
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

---

## 🎯 Próximas Validaciones (Opcional)

1. **Crea múltiples usuarios** con diferentes equipos favoritos
2. **Verifica que cada usuario** respeta su equipo seleccionado
3. **Abre packs adicionales** (BRONZE, GOLD) - verificar rarity distribution
4. **Juega una partida** para validar que el resto del juego no se rompió

---

## 📝 Notas

- Los datos se obtienen de la API real de MLB (statsapi.mlb.com)
- Las cartas se crean bajo demanda durante el seed
- Si el API falla, las cartas que se carguen serán incompletas
- Para ambiente de producción, guardar datos en caché estático

