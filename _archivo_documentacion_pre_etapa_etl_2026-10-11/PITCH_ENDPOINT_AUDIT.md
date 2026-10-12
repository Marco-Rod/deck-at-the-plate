# Auditoría: Endpoint `/pitch` - Flujo de Datos Frontend → Backend

## 🚨 PROBLEMA ENCONTRADO: 401 Unauthorized

**Error:** `POST http://localhost:8000/api/v1/games/game_d37ad39a/pitch 401 (Unauthorized)`

**Causa raíz:** El token JWT no se adjunta o está expirado/inválido en localStorage.

**Evidencia:**
```
❌ [FRONTEND] Error al enviar pitch: Error: No se pudo validar las credenciales de acceso.
```

---

## Diagrama del Problema

```
FRONTEND                           BACKEND
========================================

sendPitch(zone, pitchType)
  ✅ Payload construido correctamente:
     {"pitch_type":"4-SEAM","zone":8}
  
  ✅ GameId correcto: game_d37ad39a
  
  ❌ Token JWT: ???
     └─ localStorage.getItem('jwt_token') → ¿null? ¿expirado?
  
  ❌ Headers enviados:
     Content-Type: application/json
     Authorization: Bearer <???>  ← FALTA O INVÁLIDO
     
     └─ HTTP POST /api/v1/games/{gameId}/pitch
          ↓
          ❌ 401 Unauthorized
          
          oauth2_scheme extrae el token del header
            └─ jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                 ↓
                 ❌ PyJWTError → Token expirado o inválido
                    ↓
                    Respuesta: {"detail": "No se pudo validar las credenciales de acceso."}
```

---

## 1. Verificación del Token (Paso a Paso)

### 1.1 Abrir DevTools
- Presionar **F12**
- Ir a pestaña **Console**

### 1.2 Verificar si existe el token
Ejecutar en la consola:
```javascript
localStorage.getItem('jwt_token')
```

**Resultado esperado:**
- ✅ Si devuelve un string largo tipo `eyJhbGc...`: El token existe
- ❌ Si devuelve `null`: El token se perdió
- ❌ Si devuelve un string muy corto: El token está corrupto

### 1.3 Decodificar el token
Si el token existe, paste aquí: https://jwt.io/
- En el campo "Encoded", pega el valor del token
- Verifica:
  - `exp`: ¿Es un timestamp en el futuro?
  - `sub`: ¿Contiene el user_id?

---

## 2. Por Qué se Pierde el Token

### 2.1 Posible Causa 1: Token expirado
- **Duración del token:** 8 horas (línea 15 de `auth.py`)
- **Síntoma:** La sesión lleva > 8 horas abierta
- **Solución:** Re-loguear

### 2.2 Posible Causa 2: localStorage limpiado
- **Síntoma:** Actualizar página (F5), cerrar/abrir navegador
- **Solución:** Implementar refresh token o re-login automático

### 2.3 Posible Causa 3: Token nunca se guardó
- **Síntoma:** Login no completó exitosamente
- **Solución:** Revisar logs de login en el servidor

### 2.4 Posible Causa 4: Bug en seteo del token
- **Ubicación:** `frontend/src/utils/api.js` línea ~114-117
```javascript
const data = await response.json();
localStorage.setItem('jwt_token', data.access_token);
localStorage.setItem('user_id', data.user_id);
localStorage.setItem('username', data.username);
return data;
```
- **Problema:** ¿`data.access_token` es undefined?

---

## 3. Logs de Debugging Añadidos

### 3.1 Frontend: `api.js` (nueva línea ~30-40)
```javascript
function _buildHeaders(extra = {}) {
  const headers = { 'Content-Type': 'application/json', ...extra };
  const token = localStorage.getItem('jwt_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    console.log('🔐 [API] Token adjuntado:', token.substring(0, 20) + '...');
  } else {
    console.warn('⚠️  [API] ⚠️  NO HAY TOKEN EN LOCALSTORAGE - Solicitud sin autenticación');
  }
  return headers;
}
```

### 3.2 Frontend: `useStadiumSocket.ts` (línea ~208-216)
```typescript
const sendPitch = useCallback(
  async (zone: number, pitchType: PitchType): Promise<void> => {
    const payload: PitchPayload = { pitch_type: pitchType, zone };
    console.log('🚀 [FRONTEND] Enviando pitch al backend:');
    console.log('   payload:', JSON.stringify(payload));
    console.log('   gameId:', gameId);
    console.log('   URL esperada:', `/api/v1/games/${gameId}/pitch`);
    try {
      const response = await gamesApi.pitch(gameId, payload);
      console.log('✅ [FRONTEND] Respuesta del servidor:', response);
    } catch (error) {
      console.error('❌ [FRONTEND] Error al enviar pitch:', error);
      throw error;
    }
  },
  [gameId]
);
```

---

## 4. Cómo Debuggear

### Paso 1: Verificar token en localStorage
```javascript
// En la consola del navegador:
localStorage.getItem('jwt_token')
```

Si es `null`, **necesitas re-loguear**.

### Paso 2: Lanzar un pitch y capturar logs
1. Abre DevTools (F12)
2. Console → Limpiar logs
3. Lanza un pitch desde el juego
4. Busca los logs:
   ```
   🔐 [API] Token adjuntado: eyJhbGc...  ← ¿Aparece?
   🚀 [FRONTEND] Enviando pitch...      ← ¿Aparece?
   api.js:47 POST ... 401              ← Error de autenticación
   ❌ [FRONTEND] Error al enviar pitch
   ```

### Paso 3: Si no hay token
- El log será:
  ```
  ⚠️  [API] ⚠️  NO HAY TOKEN EN LOCALSTORAGE - Solicitud sin autenticación
  ```
- **Solución inmediata:** Cierra la partida y re-loguea

---

## 5. Soluciones Inmediatas

### 5.1 Fix Temporal (para testing)
1. Cierra el juego
2. Recarga la página (F5)
3. Asegúrate de que estés logueado
4. Vuelve a entrar a la partida

### 5.2 Fix Permanente (a implementar)
Opciones:
- **A)** Implementar refresh token (obtener nuevo JWT si expira)
- **B)** Mostrar toast "Sesión expirada, por favor re-loguea"
- **C)** Auto-refresh antes de expirar (7h 50min)

---

## 6. Verificación del Backend

El backend está **correctamente configurado**:

### `backend/app/auth.py`
```python
def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido.")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="No se pudo validar las credenciales de acceso.",
            headers={"WWW-Authenticate": "Bearer"}
        )
```

**Lo que hace:**
1. Extrae `Authorization: Bearer <token>` del header
2. Decodifica con la `SECRET_KEY`
3. Si token es válido → retorna el `user_id`
4. Si token está expirado o corrupto → 401 Unauthorized

---

## Resumen

| Aspecto | Estado |
|--------|--------|
| Payload `/pitch` | ✅ Correcto |
| HTTP Headers | ✅ Enviados |
| **Token JWT** | ❌ Falta o inválido |
| Validación backend | ✅ Correcta |
| Logs de debugging | ✅ Añadidos |

**Próximo paso:**
1. Re-loguea en la aplicación
2. Lanza un pitch nuevamente
3. Verifica los logs `🔐 [API] Token adjuntado...`
4. Confirma que el request ahora es 200 OK
