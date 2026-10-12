# Resumen: Limpieza y Fix del Problema CPU_BOT

## 🔍 Raíz del Problema Identificada

Había **DOS carpetas de frontend**:
- `frontend/` (versión antigua, descontinuada, en JSX)
- `pwa/` (versión nueva, activa, en TypeScript)

El usuario estaba corriendo **`frontend/`** sin saberlo, por eso los logs del `pwa/` no aparecían.

---

## 🧹 Limpieza Realizada

### ✅ Renombrado `frontend/` → `frontend.OLD`
- Aislado completamente
- No interfiere con el proyecto activo
- Se puede recuperar si es necesario

### ✅ Confirmado que `pwa/` es el único proyecto activo
- URL correcta: `http://localhost:5173` (del pwa)
- No hay conflictos de puertos
- No hay importaciones cruzadas

---

## 🔧 Cambios en PWA

### 1. `pwa/src/features/team/pages/RosterSelectionPage.tsx`
```typescript
// ANTES:
away_user_id: 'CPU_BOT',  ❌ Hardcodeado

// DESPUÉS:
away_user_id: config.rivalId,  ✅ Del store
```

✅ Valida que `rivalId` no esté vacío
✅ Console.logs extensos para debuggear

### 2. `pwa/src/features/lobby/store.ts`
```typescript
// Zustand store con:
config: {
  rivalId: string,  ← Se guarda cuando seleccionas rival
  gameMode: 'PVE',
  difficulty: 'MEDIUM',
  ...
}
```

✅ Persiste en memoria durante la sesión
✅ `setConfig()` actualiza correctamente

### 3. `pwa/src/features/lobby/pages/LobbyPage.tsx`
```typescript
// Carrusel de rivales:
<FranchiseCarousel
  selectedTeamId={config.rivalId}
  onSelectTeam={(rivalId) => setConfig({ rivalId })}  ✅ Guarda en store
/>
```

### 4. `pwa/src/shared/lib/i18n.ts`
```typescript
'roster.error_no_rival': 'Debes seleccionar un rival en el lobby antes de alinear.'
```

✅ Validación y mensaje de error

### 5. Backend Logs
```python
# games.py router
logger.info("[DEBUG-Router] away_user_id details: value=%s, type=%s", ...)

# game_session_service.py
logger.info("[DEBUG-Service] HOME: rival_team_id=%s", ...)
```

✅ Diagnostico del payload recibido

---

## 📊 El Flujo Correcto Ahora

```
LobbyPage:
  Usuario selecciona rival "CIN" 
  → setConfig({ rivalId: "CIN" })
  → Store Zustand: config.rivalId = "CIN"
                          ↓
RosterSelectionPage monta:
  → Lee: const config = useLobbyStore(s => s.config)
  → config.rivalId = "CIN" ✓
                          ↓
handleConfirm() construye payload:
  {
    away_user_id: config.rivalId,  // "CIN" ✓
    ...
  }
                          ↓
POST /api/v1/games/create
  Backend recibe: away_user_id="CIN" ✓
                          ↓
GameSessionService.create():
  rival_team_id = "CIN" ✓
  (CPU debería usar cartas de Cincinnati) ✓
```

---

## 🧪 Próximo Paso: PRUEBA EN VIVO

### Instrucciones en: `INSTRUCCIONES_PRUEBA_PWA.md`

1. Asegurar que estás en `pwa/` (no `frontend`)
2. Navegar al Lobby
3. Seleccionar rival
4. Ir a RosterSelectionPage
5. Alinear y hacer clic en "Iniciar Partida"
6. **Capturar todos los logs** (console + backend)

### Resultados Esperados:
- ✅ Console muestra `[DEBUG-RosterSelectionPage] rivalId: "CIN"` (o tu equipo)
- ✅ Backend recibe `away_user_id=CIN` (no `CPU_BOT`)
- ✅ Partida se crea exitosamente
- ✅ No hay error de "No hay cartas para equipo CPU_BOT"

---

## 📁 Estado del Proyecto

```
deck-at-the-plate/
├── backend/            ← Sin cambios (solo logs agregados)
├── pwa/                ← PROYECTO ACTIVO ✅
│   ├── src/
│   │   ├── features/
│   │   │   ├── lobby/
│   │   │   │   ├── pages/LobbyPage.tsx    ✅ Modif
│   │   │   │   ├── store.ts               ✅ Check
│   │   │   │   └── api.ts                 ✅ Check
│   │   │   └── team/
│   │   │       └── pages/RosterSelectionPage.tsx  ✅ Modif
│   │   └── shared/lib/i18n.ts             ✅ Modif
│   └── vite.config.ts
│
├── frontend.OLD/       ← DESCONTINUADO (aislado)
│
└── [otros archivos de documentación]
```

---

## 🎯 Conclusión

El problema fue una **colisión de dos proyectos Frontend**. 

Ahora que está limpio:
- `pwa/` es el único proyecto
- Las modificaciones están en el lugar correcto
- Los logs están en su lugar
- Solo falta **probar en vivo** para confirmar que funciona

