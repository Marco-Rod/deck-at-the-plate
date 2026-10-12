# Implementación: Modal de Cambio de Pitcher del Rival (Con Bloqueo)

## 📋 Resumen

Cuando la CPU (rival) cambia de pitcher, el flujo debe:

1. ✅ Backend envia evento `PITCHER_CHANGED` vía WebSocket
2. ✅ Backend marca `awaiting_pitcher_change_acknowledgment = True` en state
3. ⏳ **Frontend: Abre modal con ambos pitchers (salió/entró)**
4. ⏳ **Frontend: Bloquea TODO gameplay hasta que usuario haga clic en "Entendido"**
5. ⏳ **Frontend: Llama a `POST /acknowledge-pitcher-change` al backend**
6. ✅ **Backend: Limpia el flag `awaiting_pitcher_change_acknowledgment`**
7. ✅ **Gameplay continúa normalmente**

## 🔧 Cambios Implementados en Backend

### ✅ 1. Cambio en `_execute_cpu_pitcher_change()` 
Agregó flags al state:
```python
state["awaiting_pitcher_change_acknowledgment"] = True
state["pending_pitcher_change"] = {
    "old_pitcher_id": old_pitcher_id,
    "new_pitcher_id": new_pitcher.id,
}
```

### ✅ 2. Nuevo Endpoint: `/acknowledge-pitcher-change`
```
POST /api/v1/games/{game_id}/acknowledge-pitcher-change
```
Limpia los flags y desbloqueael juego.

### ✅ 3. Validación en `/pitch` y `/swing`
```python
if state.get("awaiting_pitcher_change_acknowledgment"):
    raise HTTPException(403, "El rival cambió de pitcher. Confirma el cambio antes de continuar.")
```

## ⏳ Cambios Pendientes en Frontend

### Paso 1: Agregar Estado en StadiumShowcaseScreen

```typescript
// En StadiumShowcaseScreen.tsx
const [showRivalPitcherChangeAck, setShowRivalPitcherChangeAck] = useState(false);
const [rivalPitcherChangeData, setRivalPitcherChangeData] = useState<{
  oldPitcher: PlayerData | null;
  newPitcher: PlayerData | null;
}>(null);
```

### Paso 2: Manejar el Evento PITCHER_CHANGED

En `useStadiumSocket`, agregar a callbacks:

```typescript
{
  onPitcherChanged: (payload: any) => {
    console.log('🔔 [RIVAL PITCHER CHANGE] Abriendo modal...');
    
    setRivalPitcherChangeData({
      oldPitcher: payload.old_pitcher_data, // Necesita ser agregado en backend
      newPitcher: payload.new_pitcher_data, // Lo que ya existe
    });
    setShowRivalPitcherChangeAck(true);
  },
}
```

### Paso 3: Agregar Modal en el JSX

```tsx
<RivalPitcherChangeModal
  isOpen={showRivalPitcherChangeAck}
  oldPitcher={rivalPitcherChangeData?.oldPitcher}
  newPitcher={rivalPitcherChangeData?.newPitcher}
  onAccept={handleAcknowledgePitcherChange}
/>
```

### Paso 4: Implementar Handler

```typescript
const handleAcknowledgePitcherChange = async () => {
  try {
    await gamesApi.acknowledgePitcherChange(gameId);
    console.log('✅ Cambio de pitcher confirmado');
    setShowRivalPitcherChangeAck(false);
    setRivalPitcherChangeData(null);
  } catch (error) {
    console.error('❌ Error confirmando cambio:', error);
  }
};
```

## 🔄 Flujo Completo

```
User envía /swing
    ↓
Backend resuelve swing
    ↓
CPU debe pichear
    ↓
CPU decide cambiar pitcher → get_cpu_pitcher_change_decision() = TRUE
    ↓
_execute_cpu_pitcher_change()
    ├─ Cambia active_pitcher
    ├─ Sets awaiting_pitcher_change_acknowledgment = TRUE
    └─ Broadcast PITCHER_CHANGED vía WebSocket
    ↓
Frontend recibe PITCHER_CHANGED
    ↓
onPitcherChanged() callback ejecutado
    ↓
Modal se abre:
├─ Muestra pitcher que salió
├─ Muestra pitcher que entró
└─ Botón "Entendido, Continuar"
    ↓
User hace clic en botón
    ↓
Frontend llama POST /acknowledge-pitcher-change
    ↓
Backend limpia awaiting_pitcher_change_acknowledgment = FALSE
    ↓
Gameplay continúa normalmente
```

## 🛡️ Validaciones de Bloqueo

**Backend valida en TODOS estos endpoints:**
- `/pitch` → Si hay cambio pendiente, retorna 403 FORBIDDEN
- `/swing` → Si hay cambio pendiente, retorna 403 FORBIDDEN
- `/steal` (opcional) → Si hay cambio pendiente, retorna 403 FORBIDDEN

**Frontend:**
- Modal tiene `pointer-events-auto` para que solo responda al modal
- El backdrop (`pointer-events-none`) hace que se vea "atrapado"
- No hay forma de cerrar sin hacer clic en "Entendido"

## ⚠️ Datos Faltantes en Backend

El evento PITCHER_CHANGED necesita:
```python
{
  "type": "PITCHER_CHANGED",
  "old_pitcher_id": "...",
  "old_pitcher_data": {  # ⏳ FALTA AGREGAR
    "id", "name", "number", "overall", "position", "rarity", "team", ...
  },
  "new_pitcher_id": "...",
  "new_pitcher": { ...existing... }, # Ya existe
  "state_data": { ...existing... },
}
```

### Fix necesario en Backend:

En `_execute_cpu_pitcher_change()`, agregar:

```python
old_pitcher_data = None
if old_pitcher_id:
    old_pitcher = db.query(PlayerCardModel).filter(PlayerCardModel.id == old_pitcher_id).first()
    if old_pitcher:
        old_pitcher_data = {
            "id": old_pitcher.id,
            "name": old_pitcher.name,
            "number": old_pitcher.number,
            "overall": old_pitcher.overall,
            "position": old_pitcher.position,
            "rarity": old_pitcher.rarity.value if old_pitcher.rarity else "COMMON",
            "team": old_pitcher.team.name if old_pitcher.team else "UNKNOWN",
            ...
        }

await manager.broadcast_to_game(game_id, {
    "type": "PITCHER_CHANGED",
    ...
    "old_pitcher_data": old_pitcher_data,  # ⭐ AGREGADO
    ...
})
```

## ✅ Verificación

1. ✅ Backend marca `awaiting_pitcher_change_acknowledgment = TRUE`
2. ✅ Backend envia evento PITCHER_CHANGED
3. ✅ Backend valida que no haya movimientos si hay cambio pendiente
4. ⏳ Frontend abre modal
5. ⏳ Frontend bloquea gameplay
6. ⏳ Frontend llama confirm endpoint
7. ✅ Backend limpia flag
8. ⏳ Gameplay continúa

