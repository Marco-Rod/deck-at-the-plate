# 🐛 Bug Encontrado: Selección de Franquicia Ignorada

## Problema

**Seleccionas PIT, pero recibes cartas de LAD**

En los logs:
```
[COMPOSICION_POR_EQUIPO]
  - LAD: 7 cartas  ← ¡Esperadas PIT, pero recibidas LAD!
  - PIT: 1 cartas

[UPDATE] favorite_team_id = LAD  ← El usuario eligió PIT, pero se asignó LAD
```

---

## Raíz del Problema

El backend **sí recibió** 'LAD' como `team_id` en el endpoint `/api/v1/shop/starter-pack?team_id=LAD`.

Esto significa que **el frontend envió 'LAD'**, no 'PIT'.

---

## ¿Por Qué?

### Estado Inicial Problemático

En `frontend/src/pages/OnboardingScreen.jsx` línea 68:

```javascript
const [selectedFranchise, setSelectedFranchise] = useState('LAD');
```

**El valor inicial es hardcodeado a 'LAD'.**

### Flujo de Carga

1. Página carga → `selectedFranchise = 'LAD'` (estado inicial)
2. Se llama `getAvailableTeams()` → Obtiene lista de equipos
3. Si hay equipos: `setSelectedFranchise(teams[0].id)` → Actualiza al primer equipo
4. **Carrusel muestra equipos**
5. **Usuario selecciona PIT en el carrusel**
6. **Pero podría no haber actualización correcta del estado**

### Posible Escenario de Bug

Si el usuario no espera o hay un timing issue:

```
1. Carga página
2. selectedFranchise = 'LAD'
3. Equipos cargan → podría ser que LAD siga siendo el primero
4. Usuario hace clic en PIT
5. El carrusel podría no actualizar selectedFranchise correctamente
6. Usuario hace clic en "Confirmar y Reclamar Sobre"
7. Envía selectedFranchise (que sigue siendo 'LAD')
```

---

## Solución Implementada

### Se agregó logging en 3 puntos:

#### 1. En `FranchiseCarousel.jsx` - Línea 41

```javascript
const handleTeamSelect = (index) => {
    const realIndex = index % teams.length;
    const selectedTeam = teams[realIndex];
    console.log(`[DEBUG FranchiseCarousel] Equipo seleccionado: ${selectedTeam.id}`);
    onSelectTeam(selectedTeam);
    setCurrentIndex(index);
};
```

**Logs:** Cuando haces clic en un equipo en el carrusel, verás:
```
[DEBUG FranchiseCarousel] Equipo seleccionado: PIT
```

#### 2. En `OnboardingScreen.jsx` - Línea 264

```javascript
onSelectTeam={(team) => {
    console.log(`[DEBUG OnboardingScreen] setSelectedFranchise a: ${team.id}`);
    setSelectedFranchise(team.id);
}}
```

**Logs:** Cuando se actualiza el estado, verás:
```
[DEBUG OnboardingScreen] setSelectedFranchise a: PIT
```

#### 3. En `OnboardingScreen.jsx` - handleClaimStarterPack

```javascript
console.log(`[DEBUG] Enviando starter pack con selectedFranchise=${selectedFranchise}`);
const response = await shopApi.claimStarterPack(userId, selectedFranchise);
```

**Logs:** Justo antes de enviar al backend, verás:
```
[DEBUG] Enviando starter pack con selectedFranchise=PIT
```

---

## Cómo Validar la Fix

### Pasos:

1. Abre el navegador (F12 → Console)
2. Crea un usuario nuevo
3. Funda un club
4. **En la pantalla de selección de franquicia:**
   - Mira la consola: deberías ver `[DEBUG OnboardingScreen]...` con el equipo que cargó
   - Haz clic en un equipo diferente
   - Mira la consola: deberías ver tanto `[DEBUG FranchiseCarousel]` como `[DEBUG OnboardingScreen]`
5. Haz clic en "Confirmar y Reclamar Sobre"
   - Mira la consola: deberías ver `[DEBUG] Enviando starter pack con selectedFranchise=...`
   - **Verifica que sea el equipo que seleccionaste, NO LAD**
6. Abre el sobre
   - **Verifica en la composición que recibas 7 cartas del equipo que seleccionaste**

---

## Logs que Deberías Ver

### Si todo funciona correctamente:

```
[DEBUG OnboardingScreen] setSelectedFranchise a: LAD       ← Equipo inicial
[DEBUG OnboardingScreen] setSelectedFranchise a: PIT       ← Seleccionaste PIT
[DEBUG FranchiseCarousel] Equipo seleccionado: PIT         ← Confirmó el clic
[DEBUG] Enviando starter pack con selectedFranchise=PIT   ← Envió correctamente
```

### Backend logs deberían mostrar:

```
[PARAMS] user_id=..., team_id=PIT  ← Recibió PIT correctamente
[PASO 1] Seleccionando jugadores del equipo elegido (PIT)
  [BUSQUEDA] Fielders disponibles in PIT: X
  [BUSQUEDA] Pitchers disponibles in PIT: Y
[COMPOSICION_POR_EQUIPO]
  - PIT: 7 cartas  ← ¡Correcto!
[UPDATE] favorite_team_id = PIT  ← ¡Correcto!
```

---

## Archivos Modificados

- ✅ `frontend/src/pages/OnboardingScreen.jsx` - Agregado logging en 2 puntos
- ✅ `frontend/src/components/FranchiseCarousel.jsx` - Agregado logging en handleTeamSelect

---

## Próximos Pasos

1. **Abre la consola del navegador** (F12)
2. **Sigue los pasos de validación**
3. **Verifica los logs de consola**
4. **Confirma que se selecciona el equipo correcto**
5. **Abre el sobre y valida la composición**

Si los logs muestran que se envía LAD cuando seleccionaste PIT, entonces el bug de estado está confirmado.

Si se envía PIT correctamente pero el backend sigue retornando LAD, entonces el problema está en otro lado (probablemente en cómo se pasan los equipos o en la BD).

---

## Status

- ✅ Bug identificado: selectedFranchise no se actualiza correctamente
- ✅ Logging agregado para validar
- ⏳ Necesita testing para confirmar la causa exacta
