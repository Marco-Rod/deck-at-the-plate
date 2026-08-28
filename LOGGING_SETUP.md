# Setup de Logging Comprehensive para Starter Pack

## Cambios Realizados

### 1. Backend Logging
Se ha agregado logging comprehensive a los siguientes archivos:

#### `backend/app/routers/shop.py`
- Importa `logging`
- Log al recibir request de `claim_starter_pack`
- Log de parámetros recibidos (`user_id`, `team_id`)
- Log de validaciones
- Log de éxito con cantidad de cartas devueltas

#### `backend/app/services/pack_service.py`
Logging detallado en cada paso de `assign_starter_pack()`:

1. **[INPUT]** - Recibe `user_id` y `team_id`
2. **[PASO 1]** - Selección de jugadores del equipo elegido
   - Cantidad de fielders y pitchers disponibles
   - Cartas seleccionadas (nombre, posición, overall, rareza)
3. **[PASO 2]** - Verificación de posiciones faltantes
   - Posiciones requeridas vs cubiertas
   - Cartas necesarias para completar 13
4. **[PASO 3]** - Cartas disponibles en otros equipos
   - Total de cartas disponibles
   - Equipo favorito del usuario
5. **[PASO 4]** - Agrupación por rareza
   - Distribución de cartas por rareza en equipo favorito
   - Distribución de cartas por rareza en otros equipos
6. **[PASO 5]** - Selección con distribución de raridades (2 SILVER, 4 BRONZE, 7 COMMON)
   - Fase 1: Desde equipo favorito
   - Fase 2: Desde otros equipos
   - Cada carta seleccionada con detalles
7. **[PASO 6]** - Fallback para llenar slots restantes
8. **[PASO 7]** - Mezcla de cartas
9. **[PASO 8]** - Resumen final
   - Composición por equipo
   - Composición por rareza (con validación vs esperado)
   - Composición por posición
10. **[PASO 9]** - Guardado en inventario
11. **[PASO 10]** - Actualización de estado del usuario
12. **[PASO 11]** - Inicialización de cartera

#### `backend/app/main.py`
- Configuración básica de logging con formato timestamped

## Scripts de Prueba

### `backend/test_starter_pack_with_logging.py`
Script standalone para probar la lógica:

```bash
cd backend
python test_starter_pack_with_logging.py
```

**Qué hace:**
1. Conecta a la BD
2. Obtiene un usuario existente con equipo
3. Ejecuta `assign_starter_pack()` con ese usuario
4. Valida:
   - Total de cartas = 13
   - Distribución de rareza: 2 SILVER, 4 BRONZE, 7 COMMON
   - Composición por equipo
   - Posiciones cubiertas
5. Muestra todas las cartas asignadas

**Salida:**
- Consola: logs en tiempo real
- `starter_pack_test.log`: archivo de log detallado

## Prueba Manual desde el Frontend

### Pasos:
1. Inicia el backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. Inicia el frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. En el navegador:
   - Ve a `http://localhost:5173`
   - Crea una nueva cuenta
   - Funda un club
   - Selecciona una franquicia
   - Abre el sobre

4. En la terminal del backend:
   - Verás todos los logs del proceso
   - Busca `[ASSIGN_STARTER_PACK]` para ver el resumen

5. Valida:
   - ¿Se reciben los parámetros correctos (`user_id`, `team_id`)?
   - ¿Se asignan 13 cartas?
   - ¿7 son del equipo elegido?
   - ¿La distribución de rareza es correcta?
   - ¿Se cubren todas las posiciones?

## Qué Buscar en los Logs

### Para validar que todo funciona:

```
[ENDPOINT] Recibido claim_starter_pack request
[PARAMS] user_id=XXXX, team_id=LAD    ← ¿Son correctos?
[VALIDATION] Usuario tiene club creado
[PASO 1] Seleccionando jugadores del equipo elegido
  [BUSQUEDA] Fielders disponibles en LAD: 7    ← ¿Hay suficientes?
  [BUSQUEDA] Pitchers disponibles en LAD: 4    ← ¿Hay suficientes?
  [SELECCIONADAS] 5 fielders del equipo elegido
  [SELECCIONADAS] 2 pitchers del equipo elegido
```

### Composición esperada (paso 8):

```
[PASO 8] RESUMEN FINAL - Cartas a guardar (13 total)
  [COMPOSICION_POR_RAREZA]
    - SILVER: 2 (esperadas 2) ✓
    - BRONZE: 4 (esperadas 4) ✓
    - COMMON: 7 (esperadas 7) ✓
```

### Si algo está mal:

- **Solo 1 carta del equipo elegido**: Revisar PASO 1 - check si hay fielders/pitchers
- **Todas COMMON**: Revisar PASO 4 y 5 - check si hay cartas de otras rarezas en BD
- **Posiciones faltantes**: Revisar PASO 2 y PASO 5 - la lógica de cobertura de posiciones

## Tips de Debugging

1. **Enable DEBUG logs:**
   En `backend/app/main.py`, cambia:
   ```python
   logging.basicConfig(level=logging.DEBUG, ...)
   ```

2. **Guardar logs a archivo:**
   El script de prueba ya lo hace en `starter_pack_test.log`

3. **Filtrar logs específicos:**
   ```bash
   grep "\[PASO" starter_pack_test.log
   grep "SILVER\|BRONZE\|COMMON" starter_pack_test.log
   ```

4. **Ver composición final:**
   ```bash
   grep "COMPOSICION" starter_pack_test.log -A 10
   ```
