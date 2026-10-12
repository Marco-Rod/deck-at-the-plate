# 🎯 Análisis Completo: Flujo de Selección de Rival

**Fecha:** 2026-08-30  
**Análisis realizado sobre:** PWA en `pwa/src/` con Zustand + React Router + TypeScript  
**Status:** ✅ ANÁLISIS COMPLETO

---

## 📊 Estructura del PWA - Resumen Ejecutivo

### Patrón Arquitectónico: **Feature-Based + Zustand Stores**

```
pwa/src/
├── app/                          ← Configuración de la aplicación
│   ├── App.tsx                   ← Componente root
│   ├── routes.tsx                ← Definición de rutas
│   └── providers.tsx             ← Wrappers (i18n, router, etc.)
│
├── features/                     ← Lógica por feature
│   ├── auth/
│   │   ├── store.ts              ← Zustand: user, token
│   │   ├── api.ts                ← Endpoints: login, register
│   │   └── pages/AuthPage.tsx    ← Componente
│   │
│   ├── lobby/                    ← 🎯 NUESTRO FOCO
│   │   ├── store.ts              ← Zustand: config de partida
│   │   ├── api.ts                ← Endpoints: getCpuTeams()
│   │   └── pages/LobbyPage.tsx   ← Componente
│   │
│   ├── team/
│   │   ├── store.ts              ← Zustand: user team, inventory
│   │   ├── api.ts                ← Endpoints: getLineup(), saveLineup()
│   │   ├── rosterStore.ts        ← Zustand: roster temporal
│   │   └── pages/
│   │       ├── MyTeamPage.tsx
│   │       └── RosterSelectionPage.tsx  ← 🎯 CONECTA CON LOBBY
│   │
│   ├── game/                     ← Gameplay
│   ├── cards/                    ← Cartas
│   ├── shop/                     ← Shop
│   └── onboarding/               ← Onboarding
│
├── shared/                       ← Código reutilizable
│   ├── api/
│   │   ├── client.ts             ← Axios instance
│   │   ├── types.ts              ← Tipos compartidos
│   │   └── errors.ts             ← Manejo de errores
│   ├── ui/                       ← Componentes UI
│   ├── hooks/                    ← Custom hooks
│   └── lib/                      ← Utilidades
│
└── test/                         ← Tests

```

---

## 🔄 Flujo Completo: Lobby → Roster → Backend

### PASO 1: Usuario Entra a Lobby

**Archivo:** `pwa/src/features/lobby/pages/LobbyPage.tsx`  
**Línea:** ~1-50

```typescript
export function LobbyPage() {
  const config = useLobbyStore((s) => s.config)  // ← Lee config del store
  const setConfig = useLobbyStore((s) => s.setConfig)  // ← Modifica config
  
  const [teams, setTeams] = useState<Franchise[]>([])
  
  useEffect(() => {
    getCpuTeams()  // ← API: GET /api/v1/teams/cpu
      .then(setTeams)
      .catch(() => setLoadError(t('lobby.error_load')))
  }, [t])
```

**¿Qué sucede?**
1. LobbyPage se monta
2. useEffect dispara `getCpuTeams()` (llamada API)
3. API retorna lista de equipos (Franchises)
4. `setTeams()` guarda equipos en estado local (useState)
5. Se renderiza FranchiseCarousel con la lista

**Estado actual del Store:**
```typescript
config = {
  rivalId: '',           // ← VACÍO al inicio
  gameMode: 'PVE',
  difficulty: 'MEDIUM',
  innings: 9,
  playerPosition: 'HOME',
}
```

---

### PASO 2: Usuario Selecciona Rival en Carrusel

**Archivo:** `pwa/src/features/lobby/pages/LobbyPage.tsx`  
**Línea:** ~175-190

```typescript
<FranchiseCarousel
  teams={teams}
  selectedTeamId={config.rivalId}
  onSelectTeam={(rivalId) => setConfig({ rivalId })}  // ← AQUI OCURRE LA SELECCIÓN
/>
```

**¿Qué sucede?**
1. Usuario hace clic en un equipo del carrusel
2. FranchiseCarousel dispara `onSelectTeam(rivalId)`
3. `setConfig({ rivalId })` actualiza el Zustand store
4. Zustand actualiza `config.rivalId` con el ID del equipo

**Estado del Store después:**
```typescript
config = {
  rivalId: 'NYY',        // ← ACTUALIZADO
  gameMode: 'PVE',
  difficulty: 'MEDIUM',
  innings: 9,
  playerPosition: 'HOME',
}
```

**Verificación visual:** El carrusel muestra el equipo seleccionado

---

### PASO 3: Usuario Hace Clic en "INICIAR PARTIDA"

**Archivo:** `pwa/src/features/lobby/pages/LobbyPage.tsx`  
**Línea:** ~265+

```typescript
<Button
  size="lg"
  disabled={!config.rivalId}  // ← Botón deshabilitado si no hay rival
  onClick={handleCreate}
  className="..."
>
  {t('lobby.start_pve', { innings: config.innings })}
</Button>

const handleCreate = useCallback(() => {
  navigate('/roster/pending')  // ← NAVEGA A ROSTER
}, [navigate])
```

**¿Qué sucede?**
1. Usuario hace clic en botón
2. `handleCreate()` se ejecuta
3. `navigate('/roster/pending')` redirige a RosterSelectionPage
4. El config del store persiste (Zustand usa memoria)
5. RosterSelectionPage puede acceder a `config.rivalId`

**Estado del Store (persiste):**
```typescript
config = {
  rivalId: 'NYY',        // ← ✅ PERSISTE EN ZUSTAND
  gameMode: 'PVE',
  difficulty: 'MEDIUM',
  innings: 9,
  playerPosition: 'HOME',
}
```

---

### PASO 4: Usuario Llega a Roster Selection

**Archivo:** `pwa/src/features/team/pages/RosterSelectionPage.tsx`  
**Línea:** ~1-50

```typescript
export function RosterSelectionPage() {
  const config = useLobbyStore((s) => s.config)  // ← LEE config del store
  const [lineup, setLineup] = useState<Record<string, string>>({})
  const [deck, setDeck] = useState<string[]>(['t1', 't2', 't3', 't4', 't1'])
  
  // config.rivalId ya está disponible aquí
  // config.playerPosition ya está disponible aquí
  // etc.
}
```

**¿Qué sucede?**
1. RosterSelectionPage se monta
2. Lee `config` desde Zustand store
3. `config.rivalId = 'NYY'` está disponible
4. Usuario alinea jugadores (local state: lineup)
5. Usuario selecciona mazo táctico (local state: deck)

**Estado mixto:**
```typescript
// Del Zustand store (persiste)
config.rivalId = 'NYY'

// Del componente (local)
lineup = { '1': 'card_001', '2': 'card_002', ... }
deck = ['t1', 't2', 't3', 't4', 't1']
```

---

### PASO 5: Usuario Hace Clic en "INICIAR PARTIDA" en Roster

**Archivo:** `pwa/src/features/team/pages/RosterSelectionPage.tsx`  
**Línea:** ~85-145

```typescript
const handleConfirm = async () => {
  if (!user) return
  const filledSlots = Object.values(lineup).filter(Boolean)
  if (filledSlots.length === 0) {
    setError(t('roster.error_empty'))
    return
  }
  
  setSubmitting(true)
  setError(null)
  
  try {
    // Construir payload con datos de Zustand + componente local
    const isHome = config.playerPosition === 'HOME'
    const rivalTeamId = config.rivalId || 'JAL'  // ← AQUI LEE rivalId
    
    const userBattingLineup: string[] = Object.keys(lineup)
      .sort((a, b) => Number(a) - Number(b))
      .map((spot) => lineup[spot])
      .filter((id): id is string => Boolean(id))
    
    const payload: CreateGameRequest = {
      home_user_id: user.userId,
      away_user_id: rivalTeamId,  // ← ✅ AQUI ENVÍA rivalTeamId
      game_mode: config.gameMode || 'PVE',
      difficulty: config.difficulty || 'MEDIUM',
      total_innings: config.innings || 9,
      player_position: config.playerPosition || 'HOME',
      home_pitcher_id: isHome ? userPitcherId : undefined,
      away_pitcher_id: !isHome ? userPitcherId : undefined,
      home_lineup: isHome ? userBattingLineup : [],
      away_lineup: !isHome ? userBattingLineup : [],
      home_tactics_deck: isHome ? deck : ['t1', 't2', 't3', 't4', 't1'],
      away_tactics_deck: !isHome ? deck : ['t1', 't2', 't3', 't4', 't1'],
    }
    
    // ENVIAR AL BACKEND
    const game = await createGame(payload)
    
    if (gameId && game.id !== gameId) {
      navigate(`/game/${game.id}`, { replace: true })
    } else {
      navigate(`/game/${game.id}`)
    }
  } catch {
    setError(t('roster.error_generic'))
  } finally {
    setSubmitting(false)
  }
}
```

**¿Qué sucede?**
1. Valida que hay bateadores en lineup
2. Construye payload con:
   - `rivalTeamId` del store (ej. `'NYY'`)
   - `userBattingLineup` del estado local
   - `deck` del estado local
   - Configuración del store (gameMode, difficulty, innings, position)
3. Llama a `createGame(payload)` (API endpoint)
4. Backend recibe payload y crea partida
5. Navega a `/game/{gameId}`

**Payload enviado al backend:**
```json
{
  "home_user_id": "user_123",
  "away_user_id": "NYY",                    // ← rivalId del store
  "game_mode": "PVE",                       // ← store
  "difficulty": "MEDIUM",                   // ← store
  "total_innings": 9,                       // ← store
  "player_position": "HOME",                // ← store
  "home_pitcher_id": "pitcher_456",         // ← calculado
  "away_pitcher_id": null,
  "home_lineup": ["card_001", "card_002", ...],  // ← local
  "away_lineup": [],
  "home_tactics_deck": ["t1", "t2", "t3", "t4", "t1"],
  "away_tactics_deck": ["t1", "t2", "t3", "t4", "t1"]
}
```

---

## ✅ Validación del Flujo

### 1️⃣ ¿Persiste rivalId desde Lobby a Roster?

**Respuesta: SÍ ✅**

**Mecanismo:**
- Zustand store `useLobbyStore` es singleton (se crea una sola instancia)
- Todos los componentes que accedan a `useLobbyStore()` leen/escriben en la MISMA store
- LobbyPage actualiza `config.rivalId` en Zustand
- RosterSelectionPage lee `config.rivalId` desde la MISMA instancia

**Evidencia:**
```typescript
// LobbyPage
const config = useLobbyStore((s) => s.config)
const setConfig = useLobbyStore((s) => s.setConfig)
setConfig({ rivalId: 'NYY' })  // ← Actualiza store

// RosterSelectionPage (mismo store, mismo dato)
const config = useLobbyStore((s) => s.config)
console.log(config.rivalId)  // ← Retorna 'NYY' ✅
```

---

### 2️⃣ ¿Se envía rivalId al backend?

**Respuesta: SÍ ✅**

**Mecanismo:**
- RosterSelectionPage lee `config.rivalId` del store
- Lo asigna a `rivalTeamId`
- Lo incluye en `away_user_id` del payload
- Backend recibe `away_user_id = 'NYY'`

**Evidencia:**
```typescript
// RosterSelectionPage línea ~105
const rivalTeamId = config.rivalId || 'JAL'  // Lee del store

// RosterSelectionPage línea ~115
const payload: CreateGameRequest = {
  away_user_id: rivalTeamId,  // ← Incluye rivalId
  ...
}

// Backend recibe
{
  "away_user_id": "NYY"  // ✅
}
```

---

### 3️⃣ ¿Qué sucede si rivalId es undefined?

**Situación:**
```typescript
const rivalTeamId = config.rivalId || 'JAL'
```

**Análisis:**
- Si `config.rivalId` es vacío string `''`, se usa fallback `'JAL'`
- Si `config.rivalId` es `undefined`, se usa fallback `'JAL'`
- `'JAL'` es un ID que NO existe en la BD (según PWA_ANALYSIS.md)

**Resultado:**
- ❌ Backend busca equipo con `team_id = 'JAL'`
- ❌ No encuentra cartas
- ❌ Fallback silencioso (usa todas las cartas)

---

### 4️⃣ ¿Cuándo puede estar rivalId vacío?

**Escenario 1: Usuario entra a Lobby pero no selecciona rival**
- LobbyPage monta
- `config.rivalId = ''` (valor inicial en store)
- Usuario hace clic en "INICIAR PARTIDA"
- Botón está deshabilitado: `disabled={!config.rivalId}`
- ❌ No navega a Roster

**Escenario 2: Usuario cierra navegador en Lobby**
- Zustand store se pierde (no hay persistencia a localStorage)
- Usuario vuelve a abrir
- Zustand reinicia con config por defecto
- `config.rivalId = ''` nuevamente
- Usuario hace clic en botón
- Botón está deshabilitado
- ❌ No navega

**Escenario 3: Error en getCpuTeams()**
- API falla: `getCpuTeams()` rechaza
- No hay equipos en el carrusel
- Usuario no puede seleccionar rival
- `config.rivalId = ''`
- Botón deshabilitado
- ❌ No navega

---

## 🔍 Análisis de Código - Estándares PWA_ANALYSIS.md

### ✅ Lo que se hace BIEN

1. **Feature-Based Architecture** (Regla 2.1 del analysis)
   ```
   ✅ Cada feature tiene su propia carpeta: auth/, lobby/, team/, game/
   ✅ Separación clara de responsabilidades
   ✅ Fácil de mantener y escalar
   ```

2. **Zustand Store** (Regla 4.1 del analysis)
   ```typescript
   ✅ Un store por feature (useLobbyStore, useAuthStore, etc.)
   ✅ Estado centralizado (config de partida en un solo lugar)
   ✅ Selectores tipados (selectUser, selectTeam, etc.)
   ```

3. **TypeScript Estricto** (Regla 1.1)
   ```typescript
   ✅ LobbyConfig tipado (interface con rivalId: string)
   ✅ CreateGameRequest tipado (tipos compartidos en shared/api/types.ts)
   ✅ No hay 'any' visible
   ```

4. **Acceso a Store en Componentes** (Regla 4.4)
   ```typescript
   ✅ useLobbyStore((s) => s.config)  // Selector primitivo
   ✅ Evita re-renders innecesarios
   ```

5. **Validación UI** (Regla 2.9)
   ```typescript
   ✅ Botón deshabilitado si !config.rivalId
   ✅ Previene navegación sin rival
   ```

---

### ⚠️ Lo que podría MEJORAR

1. **Persistencia de Zustand** (Regla 4.5 del analysis)
   ```typescript
   ❌ NO hay middleware persist en LobbyStore
   ❌ Si usuario recarga página, config se pierde
   ❌ Recomendación: Agregar persist middleware
   
   // Debería ser:
   export const useLobbyStore = create<LobbyState>(
     persist(
       (set) => ({ ... }),
       { name: 'lobby-config' }
     )
   )
   ```

2. **Fallback Inseguro** (Regla 1.2, valor por defecto)
   ```typescript
   ❌ const rivalTeamId = config.rivalId || 'JAL'
   ❌ 'JAL' no existe en la BD
   ❌ Debería validar o usar valor conocido
   
   // Mejor:
   if (!config.rivalId) {
     throw new Error('Rival no seleccionado')
   }
   const rivalTeamId = config.rivalId
   ```

3. **Sin Logging** (Debugging)
   ```typescript
   ❌ No hay console.log() para rastrear selecciones
   ❌ Difícil de debuggear si algo falla
   ❌ Recomendación: Agregar logs de configuración
   ```

4. **Error Handling Genérico** (Regla 5.5)
   ```typescript
   ❌ .catch(() => setLoadError(t('lobby.error_load')))
   ❌ Pierde detalle del error
   ❌ Debería loguear error completo
   ```

---

## 📋 Checklist - Validación del Flujo

- [x] ✅ LobbyStore existe y tiene `rivalId`
- [x] ✅ LobbyPage lee config del store
- [x] ✅ FranchiseCarousel permite seleccionar rival
- [x] ✅ Selección actualiza store (setConfig({ rivalId }))
- [x] ✅ Botón deshabilitado si no hay rival
- [x] ✅ handleCreate navega a /roster/pending
- [x] ✅ RosterSelectionPage lee config del store
- [x] ✅ rivalId está disponible en Roster
- [x] ✅ payload incluye away_user_id (rivalId)
- [x] ✅ createGame() envía payload al backend
- [x] ✅ Backend recibe away_user_id

---

## 🚨 Problemas Encontrados

### Problema 1: Sin Persistencia en Reload
**Severidad:** MEDIA  
**Descripción:** Si usuario recarga página en Lobby, Zustand pierde config.rivalId  
**Solución:** Agregar persist middleware  
**Estimado:** 30 min

### Problema 2: Fallback 'JAL' Inválido
**Severidad:** MEDIA  
**Descripción:** Si rivalId es undefined, usa 'JAL' que no existe en BD  
**Solución:** Validar o usar equipo conocido  
**Estimado:** 30 min

### Problema 3: Sin Logs de Debugging
**Severidad:** BAJA  
**Descripción:** Difícil rastrear si la selección se persiste  
**Solución:** Agregar console.log() en puntos clave  
**Estimado:** 15 min

---

## ✨ Conclusión

**El flujo de selección de rival FUNCIONA CORRECTAMENTE:**

1. ✅ Usuario selecciona rival en Lobby
2. ✅ Zustand persiste `config.rivalId` en memoria
3. ✅ RosterSelectionPage accede a `config.rivalId`
4. ✅ `away_user_id` se envía al backend con el rivalId correcto

**El mecanismo de persistencia es Zustand (memoria en sesión).**

**Para persistencia más robusta (reloads, múltiples tabs):**
- Agregar `persist` middleware a useLobbyStore
- Guardar en localStorage bajo clave `'lobby-config'`

---

**Análisis Realizado:** ✅ COMPLETO  
**Validación del Flujo:** ✅ FUNCIONA  
**Recomendaciones:** ✅ DOCUMENTADAS

