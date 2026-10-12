# 🐳 Reset en Docker

## ⚡ Comando Único (Ejecutar en tu máquina local, NO dentro del contenedor)

```bash
docker exec -it baseball_backend python reset_without_prompt.py
```

## 📋 Explicación

| Componente | Descripción |
|-----------|-------------|
| `docker exec` | Ejecuta comando dentro del contenedor |
| `-it` | `-i` (interactivo) + `-t` (terminal) |
| `baseball_backend` | Nombre del contenedor (del docker-compose.yml) |
| `python reset_without_prompt.py` | Script a ejecutar |

## 🔥 Pasos Rápidos (En tu Terminal Local)

```bash
# 1. Verifica que Docker está corriendo
docker ps
# Debería listar: baseball_backend, baseball_frontend, baseball_db

# 2. Ejecuta el reset
docker exec -it baseball_backend python reset_without_prompt.py

# 3. Espera a que termine (tardará 1-2 minutos)

# 4. Si todo está bien, deberías ver:
# ✅ COMPLETADO - Base de datos lista
```

## 📊 Output Esperado

```
================================================================================
🏟️  RESET & SEED - Base de Datos MLB 2026 (No-Interactive)
================================================================================

⏳ Iniciando reset automático...

================================================================================
🧹 PASO 1: Limpiando base de datos...
================================================================================

✅ Base de datos limpiada con éxito.
   ✓ Tabla 'users' vaciada
   ✓ Tabla 'user_wallets' vaciada
   ✓ Tabla 'user_teams' vaciada
   ✓ Tabla 'user_lineups' vaciada
   ✓ Tabla 'user_card_inventories' vaciada
   ✓ Tabla 'teams' vaciada

================================================================================
📥 PASO 2: Cargando datos MLB 2026...
================================================================================

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
    ✓ Equipo ya existe en BD
    ...
[30/30] ...

✅ Seed completado exitosamente
📊 Resumen: 30 equipos x ~40 jugadores = 1200 jugadores cargados
💾 Todos los cambios se han persistido en la BD

================================================================================
✅ COMPLETADO - Base de datos lista
================================================================================

📋 Cambios aplicados:
   ✓ Todos los usuarios eliminados
   ✓ Todos los equipos recreados de 0
   ✓ ~1200 cartas cargadas con fixes
```

## ✅ Verificación Posterior

Una vez ejecutado el reset, sigue estos pasos para validar:

### 1. Abre http://localhost:5173 en tu browser

### 2. Crea un nuevo usuario
- Nombre: "Test Club"
- Siglas: "TST"
- Ciudad: cualquiera
- Estadio: cualquiera

### 3. **Importante**: Selecciona un equipo DISTINTO a LAD
- Ejemplos: SF (Giants), NYY (Yankees), BOS (Red Sox), ATL (Braves)
- Verifica en DevTools Console (F12) que aparezca: `[DEBUG] setSelectedFranchise a: SF`

### 4. Haz clic en "Confirmar y Reclamar Sobre"

### 5. Verifica en los Logs del Backend

En la terminal donde corre el contenedor (o `docker logs baseball_backend`), busca:

```
[PASO 8] RESUMEN FINAL - Cartas a guardar (13 total)
  [COMPOSICION_POR_EQUIPO]
    - SF: 7 cartas
    - LAD: 1 cartas
    - NYY: 1 cartas
    - ...
  [COMPOSICION_POR_RAREZA]
    - DIAMOND: 0 (esperadas 0) ✓
    - GOLD: 0 (esperadas 0) ✓
    - SILVER: 2 (esperadas 2) ✓ ← IMPORTANTE
    - BRONZE: 4 (esperadas 4) ✓ ← IMPORTANTE
    - COMMON: 7 (esperadas 7) ✓ ← IMPORTANTE

[PASO 10] Actualizando estado del usuario
  [UPDATE] favorite_team_id asignado a = SF (no existía) ← IMPORTANTE
```

## 🎯 Criterios de Éxito

- ✅ Script termina sin errores
- ✅ SILVER: 2 (no 0)
- ✅ BRONZE: 4 (no 0)
- ✅ COMMON: 7 (no 13)
- ✅ Equipo favorito = SF (no LAD)
- ✅ 7 cartas del equipo seleccionado

**Si todo esto aparece en los logs = TODO ESTÁ FUNCIONANDO**

## 🔍 Troubleshooting

### Error: "Cannot find module"
```bash
# El contenedor no tiene las dependencias
# Pero si está corriendo correctamente con docker-compose, debería tener todo

# Si insiste, intenta:
docker restart baseball_backend
docker exec -it baseball_backend python reset_without_prompt.py
```

### Error: "connection refused" a la BD
```bash
# La BD puede no estar lista. Verifica:
docker ps -a | grep db

# Si no está corriendo:
docker-compose up -d db
# Espera unos segundos
docker exec -it baseball_backend python reset_without_prompt.py
```

### El script tarda demasiado
- Normal si es la primera vez (obtiene datos del API de MLB)
- Puede tardar 2-5 minutos
- No interrumpas, espera a que termine

### Los logs no aparecen
```bash
# Los logs están en el contenedor. Puedes verlos con:
docker logs baseball_backend -f

# O verifica después:
docker logs baseball_backend | tail -100
```

## 🚀 Variantes del Comando

### Si necesitas reiniciar el contenedor primero:
```bash
docker-compose restart backend
docker exec -it baseball_backend python reset_without_prompt.py
```

### Si necesitas detener el contenedor:
```bash
docker-compose stop backend
docker-compose start backend
docker exec -it baseball_backend python reset_without_prompt.py
```

### Si necesitas ver los logs en tiempo real:
```bash
# Terminal 1: Ver logs
docker logs baseball_backend -f

# Terminal 2: Ejecutar reset
docker exec -it baseball_backend python reset_without_prompt.py
```

### Ver estado de contenedores:
```bash
docker ps
docker ps -a  # Incluye detenidos
docker-compose ps
```

## 📝 Script Alternativo (si quieres hacerlo paso a paso)

```bash
# Paso 1: Solo limpiar
docker exec -it baseball_backend python app/seeds/clean_db.py
# Responde: s

# Paso 2: Solo seed
docker exec -it baseball_backend python app/seeds/seed_mlb_2026.py
```

Pero recomendamos usar `reset_without_prompt.py` porque hace todo de una vez.

