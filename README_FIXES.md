# 🏟️ Fixes para Pack Assignment - Documentación Completa

## 🎯 Dos Bugs Críticos Corregidos

### Bug #1: Distribución de Rareza Incorrecta
- **Problema**: Todas las cartas COMMON (0 SILVER, 0 BRONZE, 13 COMMON)
- **Esperado**: 2 SILVER + 4 BRONZE + 7 COMMON
- **Causa**: overall siempre 70 debido a verificación de "primaryNumber" en lugar de "jerseyNumber"
- **Solución**: ✅ Corregida línea 287-289 en `seed_mlb_2026.py`

### Bug #2: Equipo Favorito No Se Respeta
- **Problema**: Frontend envía LAD aunque usuario selecciona otro equipo (SF, PIT, etc)
- **Causa**: 
  - OnboardingScreen.jsx tenía hardcodeado `selectedFranchise='LAD'`
  - pack_service.py sobrescribía favorite_team_id
- **Solución**: ✅ Corregida línea 59 en `OnboardingScreen.jsx` + líneas 457-460 en `pack_service.py`

---

## 🚀 Para Ejecutar (Docker)

### Comando Único
```bash
docker exec -it baseball_backend python reset_without_prompt.py
```

**Eso es todo.** El script hace:
1. Limpia BD completamente
2. Recarga 30 equipos MLB (~1200 cartas)
3. Aplica todos los fixes

**Tiempo**: 2-3 minutos

---

## 📋 Después de Ejecutar

1. Abre: http://localhost:5173
2. Crea usuario nuevo
3. **Selecciona equipo DISTINTO a LAD** (SF, NYY, BOS, etc)
4. Abre el sobre inicial
5. Verifica en logs del backend:

```
✓ SILVER: 2 (esperadas 2)
✓ BRONZE: 4 (esperadas 4)
✓ COMMON: 7 (esperadas 7)
✓ favorite_team_id asignado a = SF (el que seleccionaste)
✓ SF: 7 cartas en [COMPOSICION_POR_EQUIPO]
```

---

## 📁 Archivos Modificados

### Backend
- ✅ `app/seeds/seed_mlb_2026.py` - Líneas 287, 319
- ✅ `app/services/pack_service.py` - Líneas 457-460
- ✅ `app/seeds/clean_db.py` - Añadida tabla `teams`

### Frontend
- ✅ `src/pages/OnboardingScreen.jsx` - Líneas 59, 97-101

### Scripts Nuevos
- ✅ `backend/reset_without_prompt.py` - Reset automático sin interactividad
- ✅ `backend/run_complete_reset.py` - Reset con confirmación interactiva (para local)

---

## 📚 Documentación

- **`QUICK_START.md`** - Guía rápida (3 pasos)
- **`TESTING_INSTRUCTIONS.md`** - Validación detallada
- **`CHANGES_SUMMARY.md`** - Resumen técnico de cambios
- **`DOCKER_RESET_INSTRUCTIONS.md`** - Instrucciones específicas para Docker
- **`DOCKER_QUICK_COMMANDS.md`** - Referencia rápida de comandos Docker

---

## ✅ Criterios de Éxito

### En los Logs
- [ ] `SILVER: 2 (esperadas 2) ✓`
- [ ] `BRONZE: 4 (esperadas 4) ✓`
- [ ] `COMMON: 7 (esperadas 7) ✓`
- [ ] `favorite_team_id asignado a = SF` (equipo seleccionado)
- [ ] `SF: 7 cartas` en [COMPOSICION_POR_EQUIPO]

### En la UI
- [ ] 2 cards con fondo plateado/dorado (SILVER)
- [ ] 4 cards con fondo cobre (BRONZE)
- [ ] 7 cards con fondo gris (COMMON)
- [ ] OVR valores variados (70s, 80s, 90s - no todos 70)

---

## 🔍 Validación Rápida (30 segundos)

```bash
# Paso 1: Reset
docker exec -it baseball_backend python reset_without_prompt.py
# Espera a que muestre: ✅ COMPLETADO

# Paso 2: Browser
http://localhost:5173

# Paso 3: Crear usuario + seleccionar equipo (NO LAD) + abrir sobre

# Paso 4: Verificar logs
docker logs baseball_backend | tail -100
# Busca: "SILVER: 2" y "BRONZE: 4" y "COMMON: 7"

# Si ves eso = ✅ EXITOSO
```

---

## 🆘 Troubleshooting

### Las cartas siguen siendo COMMON
1. Verifica que el seed ejecutó: `docker logs baseball_backend | grep "Seed completado"`
2. Si no, re-ejecuta: `docker exec -it baseball_backend python reset_without_prompt.py`
3. Crea usuario NUEVO (los viejos tienen datos cacheados)

### Frontend sigue mostrando LAD
1. Limpia caché: Ctrl+Shift+Delete (o Cmd+Shift+Delete en Mac)
2. En DevTools (F12) → Network → Desactiva "Disable cache"
3. Recarga: Ctrl+F5 (o Cmd+Shift+R en Mac)
4. Verifica que `OnboardingScreen.jsx` línea 59 tiene `useState('')`

### Error de conexión a BD
```bash
docker-compose restart db
sleep 3
docker exec -it baseball_backend python reset_without_prompt.py
```

### El script tarda mucho
- Normal. Primera vez puede tardar 2-5 minutos (obtiene datos de API)
- No interrumpas, déjalo terminar

---

## 🎮 Próximas Validaciones

1. **Crea múltiples usuarios** con diferentes equipos
2. **Verifica que cada uno** respeta su equipo seleccionado
3. **Abre packs adicionales** (BRONZE, GOLD) - validar rarity distribution
4. **Juega partidas** - validar que el resto del juego no se rompió

---

## 📊 Cambios de Datos

### Overall (Antes vs Después)
```
Antes: todos 70
Después: 70-95 (variado según jerseyNumber)
```

### Rarity Distribution (Starter Pack)
```
Antes:    DIAMOND: 0  GOLD: 0  SILVER: 0  BRONZE: 0  COMMON: 13
Después:  DIAMOND: 0  GOLD: 0  SILVER: 2  BRONZE: 4  COMMON: 7
```

### Team Composition
```
Antes: equipo seleccionado recibe 0-1 cartas (mostly LAD)
Después: equipo seleccionado recibe 7 cartas (5 fielders + 2 pitchers)
```

---

## 🔧 Detalles Técnicos

### Fix #1: Overall Distribution
```python
# seed_mlb_2026.py línea 287
if "jerseyNumber" in player_info and number and number != "0":
    overall = 70 + (int(number) % 25)  # 70-95
```

### Fix #2: Rarity Mapping
```python
# seed_mlb_2026.py línea 319
rarity = (
    CardRarity.DIAMOND if overall >= 90
    else CardRarity.GOLD if overall >= 85
    else CardRarity.SILVER if overall >= 80
    else CardRarity.BRONZE if overall >= 75
    else CardRarity.COMMON
)
```

### Fix #3: Favorite Team
```python
# pack_service.py línea 457-460
if not user.favorite_team_id:
    user.favorite_team_id = team_id  # Solo asigna si no existe
else:
    pass  # No sobrescribe si ya existe
```

---

## 📞 Support

- **Logs Location**: `docker logs baseball_backend`
- **Script Location**: `backend/reset_without_prompt.py`
- **Config**: `docker-compose.yml`

---

**🎉 Listo para validar. Ejecuta el comando y reporta resultados.**

