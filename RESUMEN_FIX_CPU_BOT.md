# Resumen Ejecutivo: Problema de CPU_BOT

## ¿Qué es el Problema?
Backend recibe `CPU_BOT` en `away_user_id` cuando debería recibir el equipo seleccionado (ej: "CIN").

```
Error: 2026-08-30 13:53:22,005 - WARNING - No hay cartas para equipo CPU_BOT
```

## ¿Qué Cambió?
Se modificó el frontend para que:
1. ✅ Lee el `config.rivalId` del store Zustand (seleccionado en LobbyPage)
2. ✅ Lo envía como `away_user_id` en el payload
3. ✅ Se valida que no esté vacío

Se agregaron logs extensos para diagnosticar.

## El Flujo Correcto (Teórico)
```
LobbyPage:    User selecciona rival "CIN" → setConfig({rivalId: "CIN"})
                                              ↓
RosterSelectionPage:  Monta → Lee config.rivalId = "CIN" ✓
                                              ↓
handleConfirm():      Envía away_user_id: "CIN" ✓
                                              ↓
Backend:             Recibe away_user_id = "CIN" ✓
                     Interpreta como rival_team_id = "CIN" ✓
                     Crea game con away_user_id = "CPU_BOT" ✓ (correcto para PVE)
```

## El Problema Real (Desconocido)
Algo está haciendo que `CPU_BOT` siga apareciendo. Posibilidades:

### 1️⃣ El Store NO Persiste (POSIBLE)
- `useLobbyStore` está en memoria solamente
- Si `config.rivalId` es vacío al montar RosterSelectionPage
- El campo `away_user_id` quedará vacío en el payload
- Pydantic aplicará el default: `"CPU_BOT"`

**Cómo verificar**: 
- Console → `[DEBUG-RosterSelectionPage] MONTADA CON CONFIG: rivalId: ???`
- Si muestra `rivalId: ""` → ¡ESTE ES EL PROBLEMA!

### 2️⃣ El Payload NO Se Envía Correctamente (POSIBLE)
- El JSON.stringify(payload) está malformado
- O `away_user_id` está `undefined`
- Pydantic aplica default

**Cómo verificar**:
- Console → `[DEBUG-RosterSelectionPage] PAYLOAD COMPLETO A ENVIAR: { away_user_id: ???`
- Si muestra `undefined` o no aparece el campo → ¡ESTE ES EL PROBLEMA!

### 3️⃣ Hay un Bug de Network/Serialización (POCO PROBABLE)
- El request se malforma en tránsito
- Backend recibe `null` o `undefined`

**Cómo verificar**:
- DevTools → Network tab
- Ver el request exacto que se envía
- Backend logs → `[DEBUG-Router] away_user_id details: value=???`

## Archivos Modificados (Lista Completa)

### Frontend (PWA)
```
✅ pwa/src/features/team/pages/RosterSelectionPage.tsx
   - Cambio: away_user_id: config.rivalId  (antes: 'CPU_BOT' hardcodeado)
   - Validación: if (!config.rivalId) setError(...)
   - Logs: Debug logs extensos
   
✅ pwa/src/shared/lib/i18n.ts
   - Cambio: Agregado 'roster.error_no_rival'
```

### Backend (Python)
```
✅ backend/app/routers/games.py
   - Cambio: Logs de request recibido
   
✅ backend/app/services/game_session_service.py
   - Cambio: Logs de procesamiento
```

## REQUISITOS PARA PRÓXIMO DIAGNÓSTICO

Necesitamos que hagas esto EN VIVO:

### Paso 1: Prepara el entorno
1. Abre DevTools (F12) → Console tab
2. Asegúrate que backend está corriendo (para ver los logs)
3. Ten a mano un editor de texto para capturar logs

### Paso 2: Ejecuta el flujo
1. Ve a `/lobby`
2. Selecciona un rival (ej: Cincinnati, Yankees, etc.)
3. Ve a RosterSelectionPage
4. Alinea 9 jugadores
5. Haz clic en "INICIAR PARTIDA"

### Paso 3: Captura TODOS estos logs

**EN CONSOLE DEL NAVEGADOR:**
```
[DEBUG-RosterSelectionPage] MONTADA CON CONFIG: { ...}
[DEBUG-RosterSelectionPage] ANTES DE CREAR PARTIDA: { ...}
[DEBUG-RosterSelectionPage] PAYLOAD COMPLETO A ENVIAR: { ...}
```

**EN TERMINAL DEL BACKEND:**
```
[DEBUG-Router] POST /create RECIBIDO payload: ...
[DEBUG-Router] away_user_id details: ...
[DEBUG-Service] CREATE invocado con: ...
[DEBUG-Service] HOME: rival_team_id=...
```

### Paso 4: Copia y pega EXACTAMENTE lo que veas

**No parafrasees, copia textual** de:
- Console del navegador
- Logs del backend

---

## Decisiones de Diseño a Considerar Después

1. **Problema de Semantics en Schema**
   - Campo se llama: `away_user_id` (suena a user_id)
   - Realidad: es el `team_id` del rival CPU
   - **Fix futuro**: Renombrar a `rival_team_id` en el schema

2. **Zustand Store Debería Usar Persist**
   - `lobbyStore` está en memoria solamente
   - Si user hace refresh, se pierde el config
   - **Fix futuro**: Agregar `persist` middleware como en `authStore`

3. **Validación en Backend**
   - El schema tiene default `"CPU_BOT"` que sirve como fallback
   - Pero es problemático si viene `undefined`
   - **Fix futuro**: Quitar default y hacer el campo requerido

---

## Conclusión

El fix teórico está hecho. Ahora necesitamos **datos en vivo para identificar el problema real**.

Los logs que captures nos dirán exactamente dónde y por qué se pierde el `rivalId`.

