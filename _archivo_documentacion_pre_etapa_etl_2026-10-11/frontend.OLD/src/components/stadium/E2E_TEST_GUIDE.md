# Guía de Prueba E2E: Modal de Cambio de Pitcher del Rival

## 🎯 Objetivo
Verificar que cuando la CPU cambia de pitcher, se abre un modal bloqueando el gameplay hasta que el usuario lo confirme.

## 📋 Pasos de Prueba

### 1. **Preparación**
- [ ] Abre DevTools (F12) → Consola
- [ ] Ten el Docker corriendo (`docker-compose logs backend --tail=50`)
- [ ] Abre el navegador en `http://localhost:5173`

### 2. **Iniciar Juego**
- [ ] Inicia sesión
- [ ] Crea o únete a un juego 1v1 contra CPU
- [ ] Selecciona dificultad (MEDIUM o HARD para más probabilidad de cambio)
- [ ] Espera a que cargue

### 3. **Trigger del Cambio de Pitcher**
- [ ] Lanza varios pitches (8-15 aproximadamente)
- [ ] Observa en la consola del backend: `🤖 [CPU PITCHER CHANGE DECISION]`
- [ ] Si decide cambiar (CHANGE), continuarás viéndolo

**Consola Backend esperada:**
```
🤖 [CPU PITCHER CHANGE DECISION] pitches=12, fatigue=45.0%, threshold=40.0%, prob=0.75 → CHANGE
🤖 [CPU PITCHER CHANGE] Iniciando cambio de lanzador:
   - CPU Position: HOME/AWAY
   - Available Pitchers: 3
🤖 [CPU PITCHER CHANGE] ✅ Seleccionado nuevo pitcher: [NOMBRE] (OVR XX)
🤖 [CPU PITCHER CHANGE] ✅ Cambio completado y guardado en BD
```

### 4. **Verificar Modal**
- [ ] **Modal debe abrirse automáticamente** mostrando:
  - Pitcher que SALIÓ (arriba, atenuado)
  - Pitcher que ENTRÓ (abajo, resaltado con glow dorado)
  - Botón "Entendido, Continuar"

**Consola Frontend esperada:**
```
🔔 [RIVAL PITCHER CHANGE] Evento recibido. Abriendo modal...
   oldPitcher: [NOMBRE_ANTERIOR]
   newPitcher: [NOMBRE_NUEVO]
```

### 5. **Verificar Bloqueo del Gameplay**
- [ ] Intenta hacer clic en el grid de zona de pitcheo → **DEBE NO RESPONDER**
- [ ] Intenta seleccionar un pitch → **DEBE NO RESPONDER**
- [ ] Intenta hacer clic en cualquier otro botón → **DEBE NO RESPONDER**
- [ ] El único elemento activo es el modal

**Consola Frontend:** (Nada se envía, sin logs de PITCH o SWING)

### 6. **Hacer Clic en "Entendido, Continuar"**
- [ ] Haz clic en el botón
- [ ] Modal debe cerrarse suavemente

**Consola Frontend esperada:**
```
✅ [ACK PITCHER CHANGE] Enviando confirmación al servidor...
✅ [ACK PITCHER CHANGE] Confirmación recibida. El juego continúa.
```

**Consola Backend esperada:**
```
✅ [ACK PITCHER CHANGE] Usuario confirmó cambio de pitcher
   old_pitcher: [ID_ANTERIOR]
   new_pitcher: [ID_NUEVO]
PITCHER_CHANGE_ACKNOWLEDGED
```

### 7. **Verificar Continuación Normal del Juego**
- [ ] Puedes lanzar un pitch normalmente
- [ ] El nuevo pitcher debe estar en el montículo (visual)
- [ ] El juego continúa sin interrupciones

**Consola Frontend esperada:**
```
🔄 [FRONTEND] Enviando pitch al backend:
   payload: {"pitch_type":"4-SEAM","zone":5}
```

## ⚠️ Posibles Problemas y Soluciones

### Modal no abre
**Síntomas:** CPU cambia pitcher pero no aparece modal
**Causas posibles:**
- Callback `onPitcherChanged` no está conectado
- Verificar en DevTools Console que aparezca `🔔 [RIVAL PITCHER CHANGE]`

**Solución:**
- Verifica que `StadiumShowcaseScreen.tsx` tenga el callback en `useStadiumSocket`

### Gameplay no está bloqueado
**Síntomas:** Puedo lanzar pitch mientras el modal está abierto
**Causas posibles:**
- El estado `awaiting_pitcher_change_acknowledgment` no está siendo seteado correctamente

**Solución:**
- Verifica backend logs: `awaiting_pitcher_change_acknowledgment = True`

### Modal no cierra
**Síntomas:** Hago clic pero el modal queda congelado
**Causas posibles:**
- `acknowledgePitcherChange` API falla
- Handler `handleAcknowledgePitcherChange` no ejecuta

**Solución:**
- Revisa DevTools Console para ver error del API call
- Verifica que el endpoint `/acknowledge-pitcher-change` existe en backend

## 🔍 Verificación de Logs Clave

### Backend
- ✅ `🤖 [CPU PITCHER CHANGE DECISION]` - Decisión tomada
- ✅ `🤖 [CPU PITCHER CHANGE]` - Cambio iniciado
- ✅ `✅ [ACK PITCHER CHANGE]` - Usuario confirmó

### Frontend
- ✅ `🔔 [RIVAL PITCHER CHANGE]` - Evento recibido
- ✅ `✅ [ACK PITCHER CHANGE]` - Confirmación enviada

## 📊 Criterios de Éxito E2E

| Criterio | Esperado | Estado |
|----------|----------|--------|
| Modal abre automáticamente | ✅ | [ ] |
| Modal muestra ambos pitchers | ✅ | [ ] |
| Gameplay bloqueado | ✅ | [ ] |
| Botón funciona | ✅ | [ ] |
| Backend recibe confirmación | ✅ | [ ] |
| Gameplay continúa | ✅ | [ ] |
| Nuevo pitcher se ve en UI | ✅ | [ ] |

