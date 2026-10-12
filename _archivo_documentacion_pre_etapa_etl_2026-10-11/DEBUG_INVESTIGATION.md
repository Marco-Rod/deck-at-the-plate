# Investigación Completa: El Misterio de CPU_BOT

## Fecha de Error
2026-08-30 13:53:22,005 - Backend recibe "CPU_BOT" en `away_user_id`

## Estado Actual del Problema

El backend sigue recibiendo `CPU_BOT` a pesar de que hemos corregido el frontend.

### Cambios Realizados al Frontend:
✅ `RosterSelectionPage.tsx`: Ahora envía `away_user_id: config.rivalId` en lugar de hardcoded `'CPU_BOT'`
✅ `i18n.ts`: Agregamos validaciones y mensajes de error
✅ Se agregaron console.logs extensos para diagnosticar

### El Flujo DEBERÍA ser:
```
1. LobbyPage → Usuario selecciona rival (ej: "CIN")
   → setConfig({ rivalId: "CIN" })
   
2. Zustand Store: config = { rivalId: "CIN", ... }
   
3. Navegación a /roster/pending (gameId="pending")
   
4. RosterSelectionPage monta
   → Lee config.rivalId = "CIN"
   
5. Usuario alinea jugadores y hace clic en "Iniciar Partida"
   
6. handleConfirm() construye payload:
   {
     home_user_id: "user_123",
     away_user_id: "CIN",  ← ¡AQUÍ DEBE ESTAR EL TEAM_ID!
     game_mode: "PVE",
     ...
   }
   
7. POST /api/v1/games/create
   → Backend recibe away_user_id = "CIN"
   
8. GameSessionService.create():
   rival_team_id = "CIN"  ✓
   away_user_id = "CPU_BOT"  ✓ (correcto para PVE)
```

## Hipótesis: ¿Por Qué Sigue Siendo CPU_BOT?

### Hipótesis 1: config.rivalId está vacío al llegar a RosterSelectionPage
- El store de Zustand NO está persistiendo `rivalId`
- `config.rivalId === ''` cuando se monta RosterSelectionPage

### Hipótesis 2: El schema default está siendo aplicado
- `backend/app/schemas/game.py` línea 5:
  ```python
  away_user_id: Optional[str] = "CPU_BOT"
  ```
- Si el frontend envía `undefined` o `null`, Pydantic aplica el default

### Hipótesis 3: Hay un bug en Zustand
- El store no está actualizando correctamente
- O hay un scope/closure issue en React

## Soluciones a Validar

### Solución 1: Validar que Zustand persista correctamente
Agregar logs en:
- LobbyPage cuando se selecciona rival
- RosterSelectionPage cuando se monta

### Solución 2: Validar el payload exacto que se envía
Agregar JSON.stringify() del payload antes de POST

### Solución 3: Validar qué recibe el backend
Agregar logs en router y service del backend

### Solución 4: Cambiar schema para ser más explícito
Renombrar `away_user_id` → `rival_team_id` en el schema
Esto haría más claro que NO es un user_id

## Logs Agregados

### Frontend (RosterSelectionPage.tsx):
- `[DEBUG-RosterSelectionPage] MONTADA CON CONFIG:` → Muestra config completo al montar
- `[DEBUG-RosterSelectionPage] ERROR: config.rivalId está vacío:` → Si rivalId es vacío
- `[DEBUG-RosterSelectionPage] ANTES DE CREAR PARTIDA:` → Config antes de enviar
- `[DEBUG-RosterSelectionPage] PAYLOAD COMPLETO A ENVIAR:` → JSON stringified
- `[DEBUG-RosterSelectionPage] Partida creada exitosamente:` → Respuesta del backend
- `[DEBUG-RosterSelectionPage] ERROR AL CREAR PARTIDA:` → Error detalladoCaptura error

### Backend (games.py router):
- `[DEBUG-Router] POST /create RECIBIDO payload:` → Muestra campos principales
- `[DEBUG-Router] away_user_id details:` → Valor exacto y tipo de dato

### Backend (game_session_service.py):
- `[DEBUG-Service] CREATE invocado con:` → Parámetros recibidos
- `[DEBUG-Service] AWAY:` o `[DEBUG-Service] HOME:` → Lógica de mapeo

## Próximos Pasos Necesarios

1. ✅ Cambios en frontend completados
2. ✅ Logs agregados
3. 🔄 **USUARIO DEBE HACER PRUEBA EN VIVO**
   - Ir al lobby
   - Seleccionar rival (ej: Reds/CIN)
   - Ir a RosterSelectionPage  
   - Alinear jugadores
   - Hacer clic en "Iniciar Partida"
   - **CAPTURAR TODOS LOS CONSOLE.LOGS DEL NAVEGADOR**
   - **CAPTURAR TODOS LOS LOGS DEL BACKEND**
4. Analizar logs para identificar dónde se pierde el rivalId
5. Aplicar fix en el punto donde se pierde

## Archivos Modificados

- `pwa/src/features/team/pages/RosterSelectionPage.tsx` 
  - ✅ Usa config.rivalId en payload
  - ✅ Validación de rivalId no vacío
  - ✅ Console.logs extensos

- `pwa/src/shared/lib/i18n.ts`
  - ✅ Agregado `roster.error_no_rival`

- `backend/app/routers/games.py`
  - ✅ Logs de request recibido

- `backend/app/services/game_session_service.py`
  - ✅ Logs de procesamiento

## Notas Importantes

### Sobre la Semántica del Schema
El schema en `backend/app/schemas/game.py` está confuso:
- Campo se llama: `away_user_id`
- Realidad: contiene el TEAM_ID del rival CPU, no un user_id
- Backend lo interpreta como: `rival_team_id` (línea 54 en game_session_service.py)

**ISSUE FUTURO**: Esto debería renombrarse a `rival_team_id` para mayor claridad.

### Zustand Store NO está siendo reseteado
Búsqueda completada: No hay ningún `.reset()` siendo llamado en el flujo actual.

