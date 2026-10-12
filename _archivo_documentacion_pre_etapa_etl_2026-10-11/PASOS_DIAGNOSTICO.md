# Pasos para Diagnosticar el Problema de CPU_BOT

## Estado Actual
- Backend SIGUE recibiendo `CPU_BOT` en `away_user_id`
- Frontend ha sido actualizado para enviar `config.rivalId`
- Se han agregado logs extensos en frontend y backend

## Cambios Realizados

### Frontend (PWA)
1. ✅ `RosterSelectionPage.tsx` - Ahora envía el team_id correcto
2. ✅ Logs agregados para diagnosticar
3. ✅ Validación para asegurar que rivalId no está vacío

### Backend
1. ✅ `games.py` router - Logs de lo que recibe
2. ✅ `game_session_service.py` - Logs del procesamiento

## IMPORTANTE: Pasos a Ejecutar

### 1. Reinicia el backend Python
```bash
# En la terminal del backend, detén y reinicia:
# Asegúrate que los cambios en game_session_service.py estén activos
```

### 2. Abre la consola del navegador (F12)
- Abre DevTools
- Ve a la pestaña "Console"
- Esto mostrará los logs `[DEBUG-RosterSelectionPage]`

### 3. Sigue estos pasos en la aplicación:
1. Navega al Lobby (`/lobby`)
2. **OBSERVA EN CONSOLA**: Debería estar vacío de logs de RosterSelectionPage (aún no estamos ahí)
3. Selecciona un rival (ej: "Cincinnati Reds" / "CIN")
4. **OBSERVA**: El carrusel debe mostrar "1/30" o similar
5. Ajusta dificultad, innings, posición si quieres
6. Haz clic en "⚡ INICIAR 9INN" (el botón debe estar HABILITADO si seleccionaste rival)
7. Navega a la pantalla RosterSelectionPage

### 4. En RosterSelectionPage:
- **CONSOLE**: Deberías ver este log inmediatamente:
  ```
  [DEBUG-RosterSelectionPage] MONTADA CON CONFIG: {
    rivalId: "CIN",  ← ¡AQUÍ ES CRÍTICO! Debe mostrar el team_id
    gameMode: "PVE",
    difficulty: "MEDIUM",
    ...
  }
  ```

### 5. Alinea jugadores:
- Selecciona 9 bateadores
- Selecciona tácticas (opcional)
- Haz clic en "INICIAR PARTIDA ▶"

### 6. CONSOLE: Antes de que se cree la partida:
- Deberías ver este log:
  ```
  [DEBUG-RosterSelectionPage] ANTES DE CREAR PARTIDA: {
    home_user_id: "user_id_aqui",
    away_user_id: "CIN",  ← ¡DEBE SER EL TEAM_ID, NO "CPU_BOT"!
    game_mode: "PVE",
    ...
  }
  ```

### 7. CONSOLE: Después:
- Deberías ver el payload completo en JSON format

### 8. BACKEND LOGS: En la terminal del backend
- Deberías ver logs como:
  ```
  [DEBUG-Router] POST /create RECIBIDO payload: home_user_id=user_id, away_user_id=CIN, ...
  [DEBUG-Router] away_user_id details: value='CIN', type=<class 'str'>, is_empty=False
  
  [DEBUG-Service] CREATE invocado con: home_user_id=user_id, away_user_id=CIN, player_position=HOME
  [DEBUG-Service] HOME: rival_team_id=CIN (from away_user_id), away_user_id=CPU_BOT (CPU)
  ```

## ¿Qué Buscar?

### ✅ Señal de Éxito:
1. `[DEBUG-RosterSelectionPage] MONTADA CON CONFIG: rivalId: "CIN"` (o tu team_id seleccionado)
2. `[DEBUG-Router] away_user_id details: value='CIN', is_empty=False`
3. Backend recibe el team_id correcto

### ❌ Señal de Problema:
1. `[DEBUG-RosterSelectionPage] MONTADA CON CONFIG: rivalId: ""` ← ¡Store vacío!
2. `[DEBUG-Router] away_user_id details: value='CPU_BOT'` ← ¡Schema default aplicado!
3. Backend recibe `CPU_BOT`

## Si config.rivalId Está Vacío

Si ves que `rivalId` está vacío en la console, significa:
- ❌ El store NO persiste entre rutas
- ❌ O hay un bug en Zustand
- ❌ O hay un reset que no vemos

**Solución**: Tendremos que:
1. Investigar por qué no persiste
2. Cambiar el flujo de navegación
3. Pasar el rivalId explícitamente en la URL o como prop

## Si config.rivalId tiene valor pero Backend recibe "CPU_BOT"

Si ves que `rivalId` está correcto en console pero backend recibe `CPU_BOT`, significa:
- ❌ El payload no se envía correctamente
- ❌ Hay un problema en el POST request
- ❌ O el schema está aplicando default incorrectamente

**Solución**: Tendremos que:
1. Verificar el Network tab (Developer Tools → Network)
2. Ver el request exacto que se envía
3. Cambiar el schema para NO tener default value

## Tickets de Console a Capturar

Por favor, **copia y pega todos los logs de console** que veas, especialmente:
- Todos los `[DEBUG-RosterSelectionPage]`
- Todos los `[DEBUG-Router]` (del backend)
- Todos los `[DEBUG-Service]` (del backend)

Esto nos ayudará a identificar exactamente dónde se pierde el `rivalId`.

