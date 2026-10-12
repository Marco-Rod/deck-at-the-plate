# 🔄 Seed MLB 2026 - Poblar BD con Datos Reales

## 📋 Descripción

Script para poblar la base de datos con:
- **30 equipos reales de MLB** con nombres ficticios
- **~1,200 jugadores reales** (40 por equipo)
- **Stats realistas** basados en datos de MLB del 25 de Marzo 2026
- **Atributos calibrados** para el motor de gameplay

## 🔗 Fuente de Datos

**API Oficial:** [statsapi.mlb.com](https://statsapi.mlb.com)
- ✅ Sin API key requerida
- ✅ Datos en tiempo real
- ✅ Acceso gratuito

## 📦 Dependencias

```
requests       # Para llamadas HTTP a statsapi.mlb.com
sqlalchemy     # Para ORM y persistencia en BD
```

Ya están incluidas en `requirements.txt`.

---

## 🚀 Ejecución

### Opción 1: Docker (Recomendado)

```bash
docker compose exec baseball_backend python -m app.seeds.seed_mlb_2026
```

### Opción 2: Local (Desarrollo)

Desde la raíz del proyecto (`deck-at-the-plate/`):

```bash
cd backend
python -m app.seeds.seed_mlb_2026
```

O directamente:

```bash
python app/seeds/seed_mlb_2026.py
```

---

## 📊 Qué Se Carga

### Equipos (30)
Cada equipo obtiene:
- ID y nombre ficticio (ej: NYY → "Titanes de Nueva York")
- Ciudad, estadio (generado)
- Colores (basados en colores reales)
- Badge/escudo

### Jugadores (~1,200)
Por cada jugador:
- Nombre real, número, posición
- Stats de temporada 2026 desde MLB
- **Para Bateadores:**
  - Contact (basado en AVG)
  - Power (basado en HR + RBI)
  - Vision (derivado de overall)
  
- **Para Lanzadores:**
  - Velocity (genérica + repertorio)
  - Control (basado en ERA)
  - Movement (basado en WHIP)
  - Repertorio con 3 pitcheos (4-SEAM, SLIDER, CHANGE)

### Rareza
Auto-asignada según overall:
- 58-74: COMMON
- 75-84: BRONZE
- 85-99: SILVER

---

## ⚙️ Conversión de Stats a Atributos

### Bateo
```
Contact = min(99, max(40, AVG * 100 + 20))
Power = min(99, max(40, (HR + RBI) / 2 * 0.8))
Vision = Contact * 0.70 + Overall * 0.30
```

### Pitcheo
```
Control = min(99, max(40, 110 - ERA * 10))
Movement = min(99, max(40, 130 - WHIP * 50))
Velocity = 92 (base) + variación por pitch
```

---

## 📈 Ejemplo de Salida

```
🔄 Iniciando seed de datos MLB 2026...
📅 Fecha de datos: 25 de Marzo de 2026

📥 Obteniendo equipos de MLB...
✓ Se obtuvieron 30 equipos

[1/30] 🏟️ New York Yankees → Titanes de Nueva York
    ✓ Equipo creado
    📋 Obteniendo roster de 40 jugadores...
    ✓ 40 jugadores encontrados
    ✓ 12 lanzadores + 28 bateadores agregados

[2/30] 🏟️ Boston Red Sox → Piratas de Boston
    ✓ Equipo ya existe en BD
    📋 Obteniendo roster de 40 jugadores...
    ✓ 40 jugadores encontrados
    ✓ 11 lanzadores + 29 bateadores agregados

... (28 equipos más)

✅ Seed completado exitosamente
📊 Resumen: 30 equipos x ~40 jugadores = ~1200 jugadores cargados
💾 Los cambios ya están persistidos en la base de datos.
```

---

## ⚠️ Notas Importantes

1. **Primera ejecución:** Puede tomar 5-10 minutos (llamadas HTTP a MLB)
2. **Duplicados:** Si ejecutas dos veces, evita duplicar datos:
   ```python
   # El script ya verifica: if existing_team
   # pero los jugadores se volverán a crear
   ```
3. **Rate Limiting:** MLB API tiene límites generosos pero si ejecutas múltiples veces rápido, espera 1-2 minutos

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'app'"
**Solución:** Ejecutar desde la raíz del backend:
```bash
cd backend
python -m app.seeds.seed_mlb_2026
```

### Error: "Connection refused" a MLB API
**Solución:** Verificar conexión a internet. statsapi.mlb.com debe estar accesible.

### Error: "Table 'teams' doesn't exist"
**Solución:** Las tablas se crean automáticamente, pero si falla, ejecutar:
```bash
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### Timeout en requests
**Solución:** El script intenta 10 segundos. Si es muy lento, incrementar timeout en:
```python
response = requests.get(url, timeout=20)  # Cambiar 10 por 20
```

---

## 📝 Mapeo de Equipos

| Real | Ficticio | Ciudad |
|------|----------|--------|
| NYY | Titanes de Nueva York | New York |
| BOS | Piratas de Boston | Boston |
| TB | Tormentas de Tampa | Tampa Bay |
| BAL | Águilas de Baltimore | Baltimore |
| LAD | Dodgers de Los Ángeles | Los Angeles |
| SF | Gigantes de San Francisco | San Francisco |
| (... y 24 más) | | |

---

## 🔄 Próximos Pasos

Después del seed, puedes:
1. Usar `/api/v1/teams` para listar equipos
2. Crear partidas con `POST /api/v1/games/create` (elegir equipos CPU)
3. Ver jugadores en el álbum del juego

---

## 💡 Tips

- El script es **idempotente para equipos** (no crea duplicados)
- Para **resetear todo**, ejecutar antes:
  ```bash
  python app/seeds/clean_db.py
  ```
- Stats se actualizan al 25 de Marzo 2026 (fecha de snapshot)
- Nombres reales de jugadores, atributos calibrados para balance

