# 🎮 Configuración de Rivales CPU - Todos los Equipos Disponibles

## 📋 Estado Actual

- **Total de equipos:** 34 (4 CPU + 30 MLB)
- **Todos disponibles como rivales:** ✅ SÍ
- **Endpoint:** `/api/v1/teams/cpu` retorna los 34 equipos

---

## 🚀 Configuración Lista

El sistema está configurado para que **TODOS LOS EQUIPOS** sean disponibles como rivales CPU en el carrusel de selección:

### Equipos CPU (4)
```
JAL: Charros
CUL: Tomateros
MTY: Sultanes
MXL: Águilas
```

### Equipos MLB (30)
```
NYY: Titanes de Nueva York
BOS: Piratas de Boston
LAD: Dodgers de Los Ángeles
... (27 más)
```

---

## ✅ Pasos Completados

1. ✅ Creada BD con 34 equipos (4 CPU + 30 MLB)
2. ✅ Agregado campo `is_cpu` al modelo Team
3. ✅ Cargadas ~1,200 cartas de jugadores reales
4. ✅ Actualizado endpoint `/api/v1/teams/cpu` para retornar todos los equipos
5. ✅ Cada equipo tiene:
   - Nombre ficticio
   - 40-50 jugadores reales
   - Stats calibrados (25 de Marzo 2026)
   - Overall calculado dinámicamente

---

## 🔍 Verificar Configuración

Ejecuta este comando para ver el estado actual:

```bash
docker compose exec baseball_backend python app/seeds/verify_all_cpu_available.py
```

Debería mostrar algo como:
```
📊 Total de equipos en BD: 34

🎮 Equipos disponibles como rivales CPU:
 1. JAL: Charros                     OVR:83 (14 cartas) [CPU]
 2. CUL: Tomateros                  OVR:81 (14 cartas) [CPU]
 3. MTY: Sultanes                   OVR:82 (12 cartas) [CPU]
 4. MXL: Águilas                    OVR:81 (12 cartas) [CPU]
 5. NYY: Titanes de Nueva York      OVR:78 (40 cartas)
 6. BOS: Piratas de Boston          OVR:76 (40 cartas)
... (28 más)

✅ Equipos disponibles: 34
📦 Total de cartas: 1,234
🔗 Endpoint /api/v1/teams/cpu retornará: 34 equipos

✅ ÉXITO: Todos los equipos están disponibles como rivales CPU
```

---

## 🎮 Cómo Usar

### En el Frontend - Seleccionar Rival

1. Abre el juego
2. Ve a "Modo de Juego"
3. Selecciona "Jugar vs CPU"
4. Verás un carrusel con todos los 34 equipos
5. Usa las flechas para navegar
6. Selecciona el rival deseado

### En el Backend - Crear Partida

```bash
curl -X POST http://localhost:8000/api/v1/games/create \
  -H "Content-Type: application/json" \
  -d '{
    "home_user_id": "user_123",
    "away_user_id": "LAD",  # Cualquiera de los 34 equipos
    "game_mode": "PVE",
    "difficulty": "NORMAL",
    "home_pitcher_id": "card_123",
    "away_pitcher_id": "card_456",
    "home_lineup": [...],
    "away_lineup": [...]
  }'
```

---

## 🔧 Scripts Disponibles

| Script | Propósito |
|--------|-----------|
| `verify_all_cpu_available.py` | Listar todos los equipos disponibles |
| `seed_mlb_2026.py` | Cargar 30 equipos MLB + jugadores |
| `seed_cpu_teams.py` | Cargar 4 equipos CPU |
| `diagnose_cpu_teams.py` | Diagnosticar estado de equipos CPU |

---

## 📊 Estructura de Datos

### Modelo Team
```python
{
  "id": "LAD",                              # 3 letras (ID único)
  "name": "Dodgers de Los Ángeles",         # Nombre ficticio
  "city": "Los Angeles",                    # Ciudad
  "primary_color": "#005A9C",               # Color primario
  "secondary_color": "#FFFFFF",             # Color secundario
  "is_cpu": False                           # Flag CPU (True solo para 4 equipos)
}
```

### Respuesta del Endpoint `/api/v1/teams/cpu`
```json
[
  {
    "id": "LAD",
    "name": "Dodgers de Los Ángeles",
    "city": "Los Angeles",
    "color": "#005A9C",
    "secondary_color": "#FFFFFF",
    "badge": "LAD",
    "desc": "Franquicia • 40 Jugadores",
    "ovr": 78,
    "batOvr": 76,
    "pitOvr": 80
  },
  ...
]
```

---

## 🎯 Próximas Mejoras (Opcional)

- [ ] Agregar dificultad diferenciada por equipo (Novato, Normal, Experto)
- [ ] Agregar ranking de equipos por overall
- [ ] Agregar historiales de victorias/derrotas contra cada equipo
- [ ] Crear ligas con equipos de igual nivel

