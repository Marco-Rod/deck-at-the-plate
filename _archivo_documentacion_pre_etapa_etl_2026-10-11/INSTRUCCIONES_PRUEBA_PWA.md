# Instrucciones para Probar el Fix CPU_BOT

## ✅ Cambios Realizados

1. **Renombrado `frontend/` a `frontend.OLD`**
   - El proyecto antiguo está aislado
   - Solo `pwa/` es el proyecto activo

2. **Modificado `pwa/src/features/team/pages/RosterSelectionPage.tsx`**
   - ✅ Ahora envía `away_user_id: config.rivalId` (no hardcoded `'CPU_BOT'`)
   - ✅ Valida que `rivalId` no esté vacío
   - ✅ Agregados console.logs para diagnosticar

3. **Modificado `pwa/src/features/lobby/store.ts`**
   - ✅ Store Zustand persiste `rivalId` en memoria
   - ✅ `setConfig()` actualiza correctamente

4. **Modificado `pwa/src/features/lobby/pages/LobbyPage.tsx`**
   - ✅ Cuando seleccionas rival, se guarda en store: `setConfig({ rivalId })`

5. **Modificado `backend/app/routers/games.py`**
   - ✅ Logs para ver qué payload recibe

6. **Modificado `backend/app/services/game_session_service.py`**
   - ✅ Logs para ver cómo procesa el payload

---

## 🧪 Cómo Probar

### Paso 1: Asegúrate que estás usando PWA
```bash
# Verifica que el dev server está en PWA
# Deberías ver: http://localhost:5173 o similar

# Si estabas usando `frontend`, cambiar a:
cd pwa
npm run dev
```

### Paso 2: Abre el navegador
- URL: `http://localhost:5173`
- Abre **DevTools** (F12)
- Ve a la pestaña **Console**

### Paso 3: Navega al Lobby
1. Login/Register si es necesario
2. Deberías estar en la pantalla del Lobby

### Paso 4: Selecciona un Rival
1. Busca el **carrusel de rivales** (dice "★ SELECCIONA TU RIVAL ★")
2. Selecciona un equipo (ej: Cincinnati Reds, Yankees, etc.)
3. **Observa en Console:**
   - Deberías ver logs como: `[DEBUG]...`
   - O pueden no aparecer si hay filtros activos

### Paso 5: Configura el Juego
1. Elige dificultad (EASY, MEDIUM, HARD)
2. Elige innings (3, 6, 9)
3. Elige posición (HOME o AWAY)
4. **Haz clic en el botón "⚡ INICIAR"**

### Paso 6: En RosterSelectionPage
1. Alinea 9 bateadores (selecciona cartas)
2. Selecciona tácticas (opcional)
3. **Haz clic en "INICIAR PARTIDA ▶"**

### Paso 7: Captura los Logs

**EN CONSOLE DEL NAVEGADOR** (F12):
Busca estos logs:
```
[DEBUG-RosterSelectionPage] MONTADA CON CONFIG:
[DEBUG-RosterSelectionPage] ANTES DE CREAR PARTIDA:
[DEBUG-RosterSelectionPage] PAYLOAD COMPLETO A ENVIAR:
[DEBUG-RosterSelectionPage] Partida creada exitosamente:
```

**EN TERMINAL DEL BACKEND:**
Busca estos logs:
```
[DEBUG-Router] POST /create RECIBIDO payload:
[DEBUG-Router] away_user_id details:
[DEBUG-Service] CREATE invocado con:
[DEBUG-Service] HOME:
```

---

## ✅ Éxito Si Ves:

### En Console:
```
[DEBUG-RosterSelectionPage] MONTADA CON CONFIG: {
  rivalId: "CIN",  ← ¡AQUÍ DEBE VER EL TEAM_ID!
  ...
}

[DEBUG-RosterSelectionPage] PAYLOAD COMPLETO A ENVIAR: {
  away_user_id: "CIN",  ← ¡DEBE SER EL TEAM_ID, NO "CPU_BOT"!
  ...
}
```

### En Backend:
```
[DEBUG-Router] away_user_id details: value='CIN', is_empty=False
[DEBUG-Service] HOME: rival_team_id=CIN (from away_user_id)
```

### En la Partida:
```
✅ La partida se crea exitosamente
✅ No hay error de "CPU_BOT"
```

---

## ❌ Problema Si Ves:

### En Console:
```
[DEBUG-RosterSelectionPage] MONTADA CON CONFIG: {
  rivalId: "",  ← ¡VACÍO!
  ...
}

[DEBUG-RosterSelectionPage] PAYLOAD COMPLETO A ENVIAR: {
  away_user_id: undefined,  ← ¡UNDEFINED!
  ...
}
```

### En Backend:
```
[DEBUG-Router] away_user_id details: value='CPU_BOT', is_empty=False
```

→ El store Zustand NO está persistiendo el rivalId entre componentes

---

## 📋 Qué Reportar

Si los logs NO aparecen o hay error:

1. **Copia EXACTAMENTE** los logs que ves (o que NO ves)
2. **Backend logs** que recibe
3. **Error en la consola** si hay alguno
4. **URL** donde estás accediendo (localhost:5173, etc.)

Con esa información identificaré el problema específico.

---

## 🔧 Si Algo Sale Mal

### Console logs no aparecen
- Verifica que estés en `pwa/` (no `frontend.OLD`)
- Recarga la página (F5)
- Abre DevTools ANTES de hacer clic en "Iniciar Partida"

### Backend recibe "CPU_BOT"
- El store Zustand tiene `rivalId` vacío
- Algo está reseteando el config entre LobbyPage y RosterSelectionPage

### Partida falla con 400 Bad Request
- Ver backend logs para el error exacto
- El payload podría estar malformado

