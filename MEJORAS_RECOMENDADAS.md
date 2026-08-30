# 🔧 Mejoras Recomendadas - Flujo de Rival

**Basado en:** Análisis de arquitectura PWA_ANALYSIS.md y código actual  
**Prioridad:** MEDIA  
**Estimado Total:** 2-3 horas

---

## 📌 Mejora 1: Persistencia en Reload (localStorage)

**Problema Actual:**
```typescript
// LobbyStore - SIN persistencia
export const useLobbyStore = create<LobbyState>((set) => ({
  config: DEFAULT_CONFIG,
  setConfig: (config) => set((state) => ({ config: { ...state.config, ...config } })),
  reset: () => set({ config: DEFAULT_CONFIG }),
}))
```

Si el usuario recarga la página en Lobby, `config.rivalId` vuelve a `''`.

**Solución Recomendada:**
```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Difficulty, GameMode, PlayerPosition } from '@/shared/api/types'

export interface LobbyConfig {
  rivalId: string
  gameMode: GameMode
  difficulty: Difficulty
  innings: number
  playerPosition: PlayerPosition
}

interface LobbyState {
  config: LobbyConfig
  setConfig: (config: Partial<LobbyConfig>) => void
  reset: () => void
}

const DEFAULT_CONFIG: LobbyConfig = {
  rivalId: '',
  gameMode: 'PVE',
  difficulty: 'MEDIUM',
  innings: 9,
  playerPosition: 'HOME',
}

export const useLobbyStore = create<LobbyState>(
  persist(
    (set) => ({
      config: DEFAULT_CONFIG,
      setConfig: (config) => set((state) => ({ config: { ...state.config, ...config } })),
      reset: () => set({ config: DEFAULT_CONFIG }),
    }),
    {
      name: 'deck-atpl-lobby-config',  // localStorage key
      partialize: (state) => ({ config: state.config }),  // Qué guardar
    }
  )
)

export const selectLobbyConfig = (state: LobbyState) => state.config
```

**Cambios:**
- ✅ Importar `persist` de zustand/middleware
- ✅ Envolver store en `persist()`
- ✅ Definir nombre de localStorage key
- ✅ Usar `partialize` para controlar qué se guarda

**Beneficio:** Config se mantiene aunque el usuario recargue la página

**Impacto:** MÍNIMO (no rompe nada, solo mejora)

---

## 📌 Mejora 2: Validación de rivalId Antes de Navegar

**Problema Actual:**
```typescript
const handleCreate = useCallback(() => {
  navigate('/roster/pending')  // ← No valida rivalId
}, [navigate])
```

**Solución Recomendada:**
```typescript
const handleCreate = useCallback(() => {
  // ✅ VALIDACIÓN: Asegurar que rivalId está seleccionado
  if (!config.rivalId) {
    console.warn('⚠️ [LOBBY] Rival no seleccionado')
    setRivalError(t('lobby.error_select_rival'))
    return
  }
  
  console.log('✅ [LOBBY] Navegando a Roster con config:', {
    rivalId: config.rivalId,
    gameMode: config.gameMode,
    difficulty: config.difficulty,
    playerPosition: config.playerPosition,
  })
  
  navigate('/roster/pending')
}, [navigate, config.rivalId, t])
```

**Cambios:**
- ✅ Validar `!config.rivalId`
- ✅ Mostrar error si falta
- ✅ Log de éxito con config
- ✅ Agregar `config.rivalId` a dependencies del useCallback

**Beneficio:** Doble validación (UI + lógica)

**Impacto:** MÍNIMO

---

## 📌 Mejora 3: Validación en RosterSelectionPage

**Problema Actual:**
```typescript
const handleConfirm = async () => {
  // ...
  const rivalTeamId = config.rivalId || 'JAL'  // ← Fallback inseguro
```

**Solución Recomendada:**
```typescript
const handleConfirm = async () => {
  if (!user) return
  
  // ✅ VALIDACIÓN: Verificar que rivalId existe
  if (!config.rivalId) {
    console.error('❌ [ROSTER] rivalId no encontrado en config')
    setError('Error: Rival no seleccionado. Vuelve a Lobby.')
    return
  }
  
  const filledSlots = Object.values(lineup).filter(Boolean)
  if (filledSlots.length === 0) {
    setError(t('roster.error_empty'))
    return
  }
  
  setSubmitting(true)
  setError(null)
  
  try {
    const isHome = config.playerPosition === 'HOME'
    const rivalTeamId = config.rivalId  // ← Usar directamente, sin fallback
    
    // ... resto del código
    
    const payload: CreateGameRequest = {
      home_user_id: user.userId,
      away_user_id: rivalTeamId,
      // ...
    }
    
    console.log('🚀 [ROSTER] Creando partida con:', {
      userId: user.userId,
      rivalTeamId,
      playerPosition: config.playerPosition,
      baterCount: userBattingLineup.length,
    })
    
    const game = await createGame(payload)
    
    console.log('✅ [ROSTER] Partida creada:', {
      gameId: game.id,
      homeUser: game.home_user_id,
      awayUser: game.away_user_id,
    })
    
    navigate(`/game/${game.id}`)
  } catch (err) {
    console.error('❌ [ROSTER] Error creando partida:', err)
    setError(t('roster.error_generic'))
  } finally {
    setSubmitting(false)
  }
}
```

**Cambios:**
- ✅ Validación explícita de `config.rivalId`
- ✅ Error si falta
- ✅ Eliminar fallback `'JAL'`
- ✅ Logs de debugging en 3 puntos
- ✅ Mejor manejo de errores

**Beneficio:** Previene envío de datos inválidos al backend

**Impacto:** MÍNIMO (mejora robustez)

---

## 📌 Mejora 4: Error Boundary en LobbyPage

**Problema Actual:**
```typescript
useEffect(() => {
  getCpuTeams()
    .then(setTeams)
    .catch(() => setLoadError(t('lobby.error_load')))
}, [t])
```

Pierde el error real.

**Solución Recomendada:**
```typescript
useEffect(() => {
  console.log('📍 [LOBBY] Cargando equipos CPU')
  
  getCpuTeams()
    .then((data) => {
      console.log(`✅ [LOBBY] ${data.length} equipos cargados:`, data.map(t => t.id))
      setTeams(data)
      
      // ✅ Establecer primer equipo como default si no hay rivalId
      if (data.length > 0 && !config.rivalId) {
        console.log(`📌 [LOBBY] Estableciendo primer equipo como default: ${data[0].id}`)
        setConfig({ rivalId: data[0].id })
      }
    })
    .catch((err) => {
      console.error('❌ [LOBBY] Error cargando equipos:', err)
      setLoadError(t('lobby.error_load'))
    })
}, [t, config.rivalId, setConfig])
```

**Cambios:**
- ✅ Log al iniciar carga
- ✅ Log con detalles de equipos
- ✅ Log de error específico
- ✅ Auto-establecer primer equipo si no hay rivalId
- ✅ Agregar dependencies correctas

**Beneficio:** Mejor debugging, experiencia mejorada

**Impacto:** MÍNIMO

---

## 📌 Mejora 5: Tipado Mejorado en Payload

**Problema Actual:**
```typescript
const payload: CreateGameRequest = {
  away_user_id: rivalTeamId,  // ← rivalTeamId podría no ser string
  // ...
}
```

**Solución Recomendada:**
```typescript
// En shared/api/types.ts
export interface CreateGameRequest {
  home_user_id: string
  away_user_id: string  // ← Siempre debe ser string
  game_mode: GameMode
  difficulty: Difficulty
  total_innings: number
  player_position: PlayerPosition
  home_pitcher_id?: string
  away_pitcher_id?: string
  home_lineup: string[]
  away_lineup: string[]
  home_tactics_deck: string[]
  away_tactics_deck: string[]
}

// En RosterSelectionPage
const payload: CreateGameRequest = {
  home_user_id: user.userId,
  away_user_id: rivalTeamId,  // ← TypeScript valida que es string
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
```

**Beneficio:** TypeScript valida tipos en compiletime

**Impacto:** MÍNIMO (solo mejora type safety)

---

## 📋 Plan de Implementación

### Orden Recomendado

1. **Mejora 1 (Persistencia)** - 30 min
   - Agregar `persist` middleware
   - Testear reload

2. **Mejora 4 (Logs en Lobby)** - 30 min
   - Agregar logs de debugging
   - Testear en consola

3. **Mejora 2 (Validación Lobby)** - 15 min
   - Agregar validación en handleCreate
   - Testear que muestra error

4. **Mejora 3 (Validación Roster)** - 30 min
   - Eliminar fallback 'JAL'
   - Agregar validaciones
   - Agregar logs

5. **Mejora 5 (Tipado)** - 15 min
   - Revisar tipos en shared/api/types.ts
   - Mejorar si es necesario

**Total:** 2-2.5 horas

---

## ✅ Verificación Post-Mejoras

Después de implementar, verificar:

- [ ] Zustand persiste config.rivalId en localStorage
- [ ] Botón "INICIAR PARTIDA" está deshabilitado si no hay rival
- [ ] Error muestra en UI si usuario intenta navegar sin rival
- [ ] Logs aparecen en DevTools Console
- [ ] RosterSelectionPage recibe rivalId correcto
- [ ] Backend recibe away_user_id con el rivalId
- [ ] TypeScript no reporta errores
- [ ] No hay breaking changes en UI

---

## 🎯 Resumen

Estas 5 mejoras hacen el flujo más **robusto**, **debuggeable** y **mantenible**, sin romper nada existente.

**Recomendación:** Implementar todas en orden.

