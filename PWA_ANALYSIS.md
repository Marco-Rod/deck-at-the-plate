# 📱 Análisis PWA: Conversión vs. Start from Scratch
## Deck at the Plate Frontend

**Fecha:** Agosto 2026  
**Estado Actual:** SPA monolítico (Vite + React 18 + Tailwind, sin PWA)  
**Decisión:** ✅ **Start from scratch** — nueva PWA en `pwa/` conservando el backend actual intacto  
**Objetivo:** Determinar viabilidad de conversión a PWA vs. nueva implementación

---

## 🔍 ESTADO ACTUAL DEL FRONTEND

### Tecnologías Base
| Aspecto | Versión/Implementación |
|--------|------------------------|
| React | 18.2.0 |
| Vite | 5.1.6 |
| Tailwind CSS | 3.4.1 |
| State Management | Zustand 4.5.2 (presente pero **NO UTILIZADO**) |
| Routing | Manual con `useState` (no React Router) |
| Build | Vite con plugin React |

### Arquitectura Actual
```
App.jsx (maneja TODA la navegación)
├─ currentView: 'AUTH' | 'ONBOARDING' | 'LOBBY' | 'MY_TEAM' | 'SHOWCASE' | 'ROSTER_SELECTION' | 'STADIUM'
├─ user: estado global en App (props drilling a todas las pantallas)
├─ gameConfig: pendiente de partida
└─ activeGameId: ID de partida activa

Persistencia:
├─ localStorage: jwt_token, user_id, username, game_session, game_state
└─ NO IndexedDB, NO Service Worker, NO manifest.json

Network:
├─ Axios (centralizado en api.js)
├─ WebSocket (useStadiumSocket, sin retry)
└─ NO offline queue, NO sync
```

### PWA Readiness Score: **0/10** ❌

| Requisito PWA | Estado | Impacto |
|---------------|--------|--------|
| ✅ Responsive Design | Sí (Tailwind) | Básico |
| ✅ HTTPS | Requerido en prod | Básico |
| ❌ manifest.json | No existe | CRITICAL |
| ❌ Service Worker | No existe | CRITICAL |
| ❌ Offline Support | Cero | CRITICAL |
| ❌ IndexedDB | No existe | MEDIUM |
| ❌ Icons (home screen) | No existe | MEDIUM |
| ❌ WebSocket resilience | Sin retry | CRITICAL |

---

## 🔬 ANÁLISIS CONCRETO — INVENTARIO DEL CÓDIGO Y ESTRATEGIA

### Verificación del stack (exploración real del repositorio)

| Aspecto | Realidad encontrada | Nota |
|--------|--------------------|------|
| Router | NO hay React Router; `App.jsx` navega con `useState('VIEW_NAME')` | 6 pantallas vía estado manual |
| State | Zustand 4.5.2 instalado pero **cero usos en el código** | Todo es prop drilling desde `App.jsx` |
| HTTP | `utils/api.js` (430 líneas) usa **`fetch()` nativo** | Axios está en dependencias = **peso muerto** |
| WebSocket | `useStadiumSocket.ts` (10.8KB) sin retry/reconnect | Dependencia crítica del gameplay |
| Persistencia | Solo `localStorage` | Sin IndexedDB ni versionado |
| TypeScript | Mixto: 4.5K líneas `.tsx` + 2.5K `.ts` + 2.3K `.jsx` + 742 `.js` | **Sin `tsconfig.json`**; lo compila suelto el esbuild de Vite |
| Calidad | Sin ESLint, sin Prettier, sin framework de testing | `node_modules`: 131 paquetes |
| Build | `dist/` ≈ **10.2 MB** (stadium.png 2.8MB, playbal.jpg 3.8MB, lineup.jpg 3.0MB, JS 482KB, CSS 54KB) | Sin code splitting, imágenes sin optimizar |

> ⚠️ **Corrección a secciones previas:** el código NO usa Axios (usa `fetch()` nativo en `api.js`). El Axios de `package.json` es dependencia muerta junto con Zustand.

### Inventario de archivos clave (frontend/)

| Archivo | Tamaño | Rol |
|---------|--------|-----|
| `pages/OnboardingScreen.jsx` | 24.7 KB | Selección de franquicia + apertura de starter pack |
| `pages/LobbyScreen.jsx` | 22.4 KB | Menú principal, config de partida, carrusel de rivals |
| `components/stadium/RivalPitcherChangeModal.tsx` | 20.1 KB | Ack de cambio de pitcher de la CPU |
| `components/stadium/StadiumShowcaseScreen.tsx` | 15.0 KB | **Orquestador principal del juego** (conecta hooks + componentes) |
| `components/stadium/PlayResultOverlay.tsx` | 15.5 KB | Overlay animado de eventos |
| `utils/api.js` | 14.0 KB | Cliente HTTP (auth, games, user, cards, teams, shop) |
| `pages/MyTeamScreen.jsx` | 13.9 KB | Gestión de roster |
| `components/stadium/ChangePitcherModal.tsx` | 13.5 KB | Cambio de pitcher humano |
| `components/cards/PlayerCard.jsx` | 13.1 KB | Carta de jugador |
| `hooks/useEventSequencer.ts` | 13.0 KB | Motor de secuenciación de animaciones |
| `utils/audioManager.js` | 11.0 KB | Síntesis de sonido (Web Audio API) |
| `hooks/useStadiumSocket.ts` | 10.8 KB | Conexión WebSocket |

**Resumen:** 65 archivos fuente, ~10.3K líneas. Todo el gameplay real (estadio, hooks, WebSocket) está en `.tsx`/`.ts`; las páginas de menú en `.jsx`.

### Qué se REUTILIZA (migración copia → refactor tipado)

✅ Componentes visuales: `PlayerCard`, `PitchZoneGrid`, `PitchSelector`, `StrikeZoneGrid`, `ScoreboardHeader`, `GameplayDeckAndReveal`, modales (Intro, Transition, Game Over, Result, Change Pitcher, Quit)  
✅ Lógica de hooks: `useEventSequencer`, `useStadiumSocket`, `useGameStatePersistence`, `useTacticalControls`, `useModalSequencing`  
✅ Estilos Tailwind: paleta Koshien, breakpoints custom, fonts (Teko/Courier Prime/Inter)  
✅ `utils/audioManager.js` → migrar a TS  
✅ Config de i18n (`src/i18n.js`) con traducciones ES/EN  
✅ Assets de juego: `stadium-bg.jpg`, siluetas SVG (bat/pitch)  

### Qué se DESCARTA

❌ `App.jsx` con navegación `useState` → **React Router**  
❌ Prop drilling → **Zustand** (stores por feature)  
❌ `api.js` monolítico con `fetch()` → **Axios instance** con interceptores (retry, JWT) por feature  
❌ `useStadiumSocket.ts` sin retry → **servicio WebSocket** con reconnect + fallback a polling  
❌ `dist/` (se regenera) y `frontend/` actual → queda como legado/ referencia visual  
❌ Dependencias muertas: axios-duplicado, Zustand como place-holder (ahora sí se usa), `node_modules` entero

### Árbol de directorios propuesto

```
deck-at-the-plate/
├── backend/                    ← SE CONSERVA INTACTO
├── pwa/                        ← NUEVA PWA (reemplaza frontend/ en producción)
│   ├── public/
│   │   ├── manifest.json       ← vite-plugin-pwa lo genera
│   │   ├── sw.js               ← Workbox (generado)
│   │   └── icons/              ← 192x192, 512x512, maskable
│   ├── src/
│   │   ├── main.tsx            ← entry + register SW
│   │   ├── app/
│   │   │   ├── App.tsx         ← Router
│   │   │   ├── routes.tsx      ← Definición de rutas
│   │   │   └── providers.tsx   ← Zustand + i18n + theme
│   │   ├── features/           ← Arquitectura por feature
│   │   │   ├── auth/           ← store, api, pages/AuthPage
│   │   │   ├── lobby/          ← store, api, pages/LobbyPage
│   │   │   ├── team/           ← MyTeamPage, RosterSelectionPage
│   │   │   ├── game/           ← store, hooks (ws, sequencer, persistence), components/, pages/StadiumPage
│   │   │   ├── cards/          ← PlayerCard, Showcase
│   │   │   └── shop/           ← StarterPack, OpenPack
│   │   ├── shared/
│   │   │   ├── api/            ← client.ts, interceptors.ts, types.ts
│   │   │   ├── ui/             ← Button, Modal, ... (design system)
│   │   │   ├── hooks/          ← useMediaQuery, ...
│   │   │   └── lib/            ← audio.ts, i18n.ts
│   │   ├── offline/
│   │   │   ├── sw.ts           ← registro SW (Workbox)
│   │   │   ├── db.ts           ← IndexedDB (Dexie) + versionado
│   │   │   └── sync.ts         ← cola offline + background sync
│   │   └── styles/globals.css  ← Tailwind + tema Koshien
│   ├── package.json
│   ├── tsconfig.json           ← TS estricto
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── index.html
├── frontend/                    ← LEGADO (referencia visual; se puede eliminar al final)
└── docker-compose.yml           ← se actualiza para servir pwa/
```

### Estrategia de migración (orden de construcción)

| Fase | Qué | Por qué en este orden |
|------|-----|----------------------|
| 0 | Scaffold `pwa/` (Vite + React + TS estricto + Tailwind + Router) | Base sólida antes de migrar nada |
| 1 | `shared/api` + `features/auth` | Login funcionando permite iterar contra el backend real |
| 2 | `features/lobby` + `features/team` + `cards` | Navegación básica completa |
| 3 | `features/game` (WebSocket + componentes del estadio) | El core del producto |
| 4 | PWA: manifest + Service Worker + IndexedDB + sync | Habilitar offline |
| 5 | `features/shop` + audio + i18n + performance | Completar features y pulir |
| 6 | Testing (unit/integration/E2E) + deploy | Blindar calidad y salir a producción |

> El checklist granular de cada fase vive más abajo en **📋 CONTROL DE FASES (PWA)**.

---

## 🚨 BLOQUEOS CRÍTICOS PARA PWA

### 1. **WebSocket Obligatorio + Offline Impossibility**
```typescript
// useStadiumSocket.ts
const ws = new WebSocket(wsUrl);
ws.onclose = () => {
  setIsConnected(false);
  // ❌ SIN RETRY, SIN FALLBACK A POLLING
  // ❌ SIN QUEUE DE ACCIONES OFFLINE
};
```
**Problema:** Todo el gameplay depende de WebSocket en tiempo real.
- Sin conexión = App no funciona
- No hay mecanismo para continuar offline
- No hay re-sincronización automática

**Solución necesaria:**
- Implementar service worker con WebSocket fallback a HTTP polling
- Crear queue de acciones (pitch, swing, tactic) para offline
- Re-sincronizar cuando reconecte
- Estimado: **2-3 semanas**

### 2. **State Management Disperso**
```jsx
// App.jsx
const [user, setUser] = useState(null);
const [currentView, setCurrentView] = useState('LOBBY');
const [pendingGameConfig, setPendingGameConfig] = useState(null);
const [activeGameId, setActiveGameId] = useState(null);
// ❌ ZUSTAND INSTALADO PERO NO USADO
```
**Problema:** Props drilling en 50+ componentes.
- No hay global store para estado offline-first
- Difícil gestionar sincronización de datos
- Zustand está en dependencias pero no se aprovecha

**Solución necesaria:**
- Migrar estado global a Zustand
- Crear stores para: auth, game, user, ui
- Implementar persistencia automática Zustand ↔ localStorage/IndexedDB
- Estimado: **2-3 semanas**

### 3. **Storage Limitado: localStorage Únicamente**
```typescript
// useGameStatePersistence.ts
const GAME_STATE_KEY = 'game_state_persistence';
const GAME_METADATA_KEY = 'game_metadata';
localStorage.setItem(GAME_STATE_KEY, JSON.stringify(dataToSave));
// ❌ localStorage: ~5-10MB máximo
// ❌ SIN VERSIONADO, SIN MIGRACIONES
// ❌ SIN VALIDACIÓN DE SCHEMA
```
**Problema:** localStorage es insuficiente para PWA.
- Límite de ~5-10MB por dominio
- Sin versionado de datos
- Sin migraciones automáticas
- Game state grande + múltiples partidas = overflow

**Solución necesaria:**
- Implementar IndexedDB con dexie.js (librería ligera)
- Schema con versionado
- Migraciones automáticas
- localStorage como fallback para session (JWT)
- Estimado: **1-2 semanas**

### 4. **HTTP Requests Sin Retry**
```javascript
// api.js
async function _request(path, options = {}) {
  const response = await fetch(fullUrl, {
    ...options,
    headers: _buildHeaders(options.headers || {}),
  });
  // ❌ SIN RETRY EN FALLO
  // ❌ SIN QUEUE PARA OFFLINE
  // ❌ SIN SINCRONIZACIÓN
}
```
**Problema:** Requests fallan sin mecanismo de recovery.
- Offline = error al usuario inmediatamente
- No hay queue de acciones pendientes
- No hay re-intento automático

**Solución necesaria:**
- Envolver axios con retry logic + exponential backoff
- Integrar con offline queue (sincronizar cuando online)
- Estimado: **1 semana**

### 5. **Sin Manifest.json ni Service Worker**
```html
<!-- index.html (actual) -->
<!DOCTYPE html>
<html lang="es">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <!-- ❌ NO manifest.json link -->
    <!-- ❌ NO theme-color meta -->
    <!-- ❌ NO apple-mobile-web-app-capable -->
  </head>
```
**Problema:** No hay configuración de PWA.
- Sin manifest → no se puede instalar como app
- Sin theme-color → no se ve bien en home screen
- Sin icons → no hay icono visual

**Solución necesaria:**
- Crear manifest.json con 5 versiones de iconos (192px, 512px, etc.)
- Agregar meta tags PWA
- Registrar service worker en main.jsx
- Estimado: **3-5 días**

### 6. **Zustand No Utilizado (Dependencia Muerta)**
```json
{
  "dependencies": {
    "zustand": "^4.5.2"  // ← Presente pero NO en uso
  }
}
```
**Problema:** Librería en dependencias sin beneficio actual.
- Si se implementa PWA, REQUIERE refactor a Zustand
- Eliminarla ahora = trabajo innecesario en conversión
- Mantenerla = deuda técnica

**Solución para PWA:** Refactor obligatorio.

---

## 📊 OPCIÓN 1: CONVERSIÓN A PWA (ACTUAL → PWA)

### Desglose de Tareas

#### **Fase 1: Infraestructura de Service Worker (2 semanas)**
1. Crear service worker (`public/sw.js`)
   - Cache strategy: network-first con fallback a cache
   - Caché de assets estáticos (JS, CSS, fontes)
   - Versioning automático en build
   - Líneas de código: ~400-500

2. Registrar en main.jsx
   - Detectar soporte de PWA
   - Manejar actualizaciones de SW
   - Líneas de código: ~50

3. Implementar WebSocket fallback
   - Detectar desconexión
   - Cambiar a polling HTTP (cada 2s)
   - Reconectar cuando online
   - Líneas de código: ~200-300

**Complejidad:** HIGH (lógica de comunicación actual + offline)  
**Riesgo:** MEDIUM (puede romper gameplay)  
**Estimado:** 2 semanas

---

#### **Fase 2: Refactor de State Management a Zustand (2-3 semanas)**
1. Crear stores (Zustand):
   ```typescript
   // stores/auth.ts
   export const useAuthStore = create((set) => ({
     user: null,
     token: null,
     login: (user, token) => set({ user, token }),
   }));
   
   // stores/game.ts
   export const useGameStore = create((set) => ({
     currentView: 'LOBBY',
     gameState: null,
     navigate: (view) => set({ currentView: view }),
   }));
   ```
   - Auth store (user, token, login/logout)
   - Game store (currentView, activeGameId, gameState)
   - UI store (modals, notifications)
   - Líneas de código: ~500-600

2. Migrar App.jsx
   - Reemplazar `useState` con `useAuthStore()`, `useGameStore()`
   - Actualizar handlers
   - Líneas de código: ~150-200 (reducido de 250)

3. Actualizar 50+ componentes (mínimo)
   - Props drilling → direct store access
   - useAuthStore() en lugar de props.user
   - useGameStore() en lugar de props.currentView
   - ~10-20 líneas cada uno = 500-1000 líneas totales

4. Persistencia automática Zustand
   ```typescript
   // Middleware Zustand + localStorage
   const persistedStore = persist(useAuthStore, {
     name: 'auth-storage',
   });
   ```
   - Líneas de código: ~100

**Complejidad:** VERY HIGH (refactor masivo)  
**Riesgo:** HIGH (romper múltiples pantallas)  
**Estimado:** 2.5-3 semanas

---

#### **Fase 3: IndexedDB para Persistencia (1.5-2 semanas)**
1. Diseñar schema:
   ```typescript
   // dexie setup
   const db = new Dexie('DeckAtThePlate');
   db.version(1).stores({
     gameState: '++id, gameId, userId, timestamp',
     gameHistory: '++id, userId, gameId',
     userCards: '++id, userId, cardId',
     roster: '++id, userId, gameId',
   });
   ```
   - 4 tablas mínimo
   - Versionado para migraciones futuras
   - Líneas de código: ~150-200

2. Migraciones automáticas
   ```typescript
   db.version(2).stores({
     // ← agregaciones futuras
   });
   db.version(2).upgrade((tx) => {
     // Lógica de migración
   });
   ```
   - Líneas de código: ~100-150

3. Implementar Zustand middleware para IndexedDB
   ```typescript
   // Persistir store en IndexedDB en lugar de localStorage
   const persistedStore = create(
     persist(gameStore, {
       name: 'game-store',
       storage: {
         getItem: async (key) => await db.gameState.get(key),
         setItem: async (key, val) => await db.gameState.put(val),
       },
     })
   );
   ```
   - Líneas de código: ~100-150

4. Query builders para recuperación
   - Recuperar último gameState
   - Listar partidas históricas
   - Líneas de código: ~100-150

**Complejidad:** MEDIUM (nueva librería Dexie, pero straightforward)  
**Riesgo:** MEDIUM (bugs de indexing, migraciones)  
**Estimado:** 1.5-2 semanas

---

#### **Fase 4: Offline Queue y Sincronización (1.5 semanas)**
1. Crear queue de acciones:
   ```typescript
   // stores/offlineQueue.ts
   export const useOfflineQueue = create((set) => ({
     queue: [],
     enqueue: (action) => set((s) => ({ queue: [...s.queue, action] })),
     dequeue: () => set((s) => ({ queue: s.queue.slice(1) })),
     clear: () => set({ queue: [] }),
   }));
   ```
   - Acciones permitidas offline: PITCH, SWING, TACTIC (no cambios de config)
   - Líneas de código: ~100-150

2. Wrapper para api.js
   ```javascript
   // api wrapper
   export async function requestWithQueue(method, path, data) {
     if (!navigator.onLine) {
       // Offline: enqueu action
       useOfflineQueue.getState().enqueue({ method, path, data, timestamp });
       return { queued: true };
     }
     // Online: ejecutar normal
     return _request(path, { method, ...data });
   }
   ```
   - Líneas de código: ~150-200

3. Re-sincronización cuando reconecta
   ```javascript
   // offlineQueue.ts
   window.addEventListener('online', async () => {
     const queue = useOfflineQueue.getState().queue;
     for (const action of queue) {
       await requestWithQueue(action.method, action.path, action.data);
     }
     useOfflineQueue.getState().clear();
   });
   ```
   - Líneas de código: ~100-150

**Complejidad:** MEDIUM (lógica clara pero edge cases)  
**Riesgo:** MEDIUM (conflictos de estado si servidor cambió)  
**Estimado:** 1.5 semanas

---

#### **Fase 5: Manifest.json + Icons (1 semana)**
1. Crear manifest.json:
   ```json
   {
     "name": "Deck at the Plate",
     "short_name": "Deck",
     "description": "Juego de cartas de béisbol táctico",
     "start_url": "/",
     "display": "standalone",
     "background_color": "#121619",
     "theme_color": "#8B4513",
     "orientation": "portrait-primary",
     "icons": [
       { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
       { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
       { "src": "/icons/icon-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
       { "src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
     ],
     "screenshots": [
       { "src": "/screenshots/screenshot1.png", "sizes": "540x720", "type": "image/png" },
       { "src": "/screenshots/screenshot2.png", "sizes": "540x720", "type": "image/png" }
     ]
   }
   ```

2. Actualizar index.html:
   ```html
   <link rel="manifest" href="/manifest.json">
   <meta name="theme-color" content="#8B4513">
   <meta name="apple-mobile-web-app-capable" content="yes">
   <link rel="apple-touch-icon" href="/icons/icon-180.png">
   ```

3. Generar iconos (design → PNG)
   - 192x192, 512x512, maskable versions
   - ~1 hora con tool de diseño

**Complejidad:** LOW (configuración)  
**Riesgo:** LOW  
**Estimado:** 1 semana

---

#### **Fase 6: Testing y Fixes (1-1.5 semanas)**
1. Testing en múltiples escenarios:
   - Offline → Online (sync queue)
   - WebSocket desconexión → fallback polling
   - Cambio de idioma (i18n con Zustand)
   - Múltiples tabs (Zustand broadcast)
   - Service worker updates

2. Performance profiling
   - Cache hits/misses
   - Bundle size (antes/después)
   - IndexedDB queries

3. Bug fixes y edge cases
   - Conflictos de estado si servidor cambió
   - Expiración de caché
   - Manejo de errores de red

**Estimado:** 1-1.5 semanas

---

### **TOTAL CONVERSIÓN: 9-11 semanas**

| Fase | Semanas | Riesgo | Complejidad |
|------|---------|--------|-------------|
| 1. Service Worker + WS Fallback | 2 | MEDIUM | HIGH |
| 2. Refactor Zustand | 2.5-3 | HIGH | VERY HIGH |
| 3. IndexedDB | 1.5-2 | MEDIUM | MEDIUM |
| 4. Offline Queue + Sync | 1.5 | MEDIUM | MEDIUM |
| 5. Manifest + Icons | 1 | LOW | LOW |
| 6. Testing + Fixes | 1-1.5 | MEDIUM | MEDIUM |
| **TOTAL** | **9-11** | **MEDIUM-HIGH** | **HIGH** |

### Cambios de Archivo Esperados

```
✏️ Modificado: src/App.jsx (250 → 50 líneas, eliminado estado)
✏️ Modificado: src/utils/api.js (agregado offline queue wrapper, ~150 líneas)
✏️ Modificado: vite.config.js (SW build plugin)
✏️ Modificado: package.json (agregar dexie ~5KB)
✏️ Modificado: index.html (manifest link, meta tags)
✏️ Modificado: 50+ componentes (usar stores en lugar de props)

🆕 Crear: src/stores/auth.ts (~150 líneas)
🆕 Crear: src/stores/game.ts (~200 líneas)
🆕 Crear: src/stores/ui.ts (~100 líneas)
🆕 Crear: src/stores/offlineQueue.ts (~150 líneas)
🆕 Crear: src/db/index.ts (~200 líneas, IndexedDB schema)
🆕 Crear: public/sw.js (~500 líneas, service worker)
🆕 Crear: public/manifest.json (~50 líneas)
🆕 Crear: public/icons/*.png (5 archivos, diseño)
```

### Riesgos Clave

1. **Refactor masivo de componentes** → Introducción de bugs
2. **State management refactor** → Múltiples pantallas pueden romperse
3. **WebSocket fallback** → Sincronización compleja
4. **Offline queue** → Edge cases en conflictos de estado
5. **Tech debt en el path de conversión** → Patrón híbrido (algunos componentes con Zustand, otros con props)

### Ventajas de la Conversión

✅ Reutilización de 80% del código existente  
✅ Componentes existentes funcionan (con refactoring)  
✅ Diseño visual preservado  
✅ Lógica de gameplay intacta  

### Desventajas de la Conversión

❌ Refactor masivo = alto riesgo de bugs  
❌ Tech debt híbrido durante transición  
❌ Zustand es "parche" en arquitectura antigua  
❌ Duración similar a start-from-scratch  
❌ Debugging más difícil (código antiguo + nuevo mezclado)

---

## 🆕 OPCIÓN 2: START FROM SCRATCH (PWA Nativa)

### Desglose de Tareas

#### **Fase 1: Setup PWA + Arquitectura (1 semana)**
1. Crear proyecto Vite con PWA plugins
   ```bash
   npm create vite@latest deck-pwa -- --template react-ts
   npm install vite-plugin-pwa dexie zustand axios
   ```

2. Configurar vite-plugin-pwa
   ```typescript
   // vite.config.ts
   import { VitePWA } from 'vite-plugin-pwa'
   
   export default defineConfig({
     plugins: [
       react(),
       VitePWA({
         registerType: 'autoUpdate',
         manifest: { /* ... */ },
         workbox: { /* ... */ },
       }),
     ],
   });
   ```
   - Plugin genera: manifest.json, sw.js, workbox config
   - Líneas: ~100

3. Crear Zustand stores (desde día 1)
   ```typescript
   // stores/auth.ts, game.ts, ui.ts, offlineQueue.ts
   // Implementación limpia desde cero
   // Líneas: ~600 (mismo que en conversión, pero sin deuda técnica)
   ```

4. Configurar IndexedDB (Dexie) desde inicio
   ```typescript
   // db/index.ts
   // Schema claro desde el principio
   // Líneas: ~200
   ```

5. Arquitectura de carpetas
   ```
   src/
   ├─ stores/ (Zustand)
   ├─ components/ (React)
   ├─ pages/ (pantallas principales)
   ├─ hooks/ (custom hooks)
   ├─ db/ (Dexie schema)
   ├─ services/ (API, WebSocket, offline sync)
   ├─ utils/ (helpers)
   └─ types/ (TypeScript)
   ```

**Ventaja clave:** No hay deuda técnica, arquitectura limpia desde día 1.

**Estimado:** 1 semana

---

#### **Fase 2: Componentes Core + UI (2-2.5 semanas)**
1. Reutilizar código existente (80%)
   - Copiar componentes de `components/`, `pages/` del proyecto actual
   - Reemplazar props con store access
   - Reusable: GameplayDeckAndReveal, PlayerCard, GameOverModal, etc.
   - Tiempo: ~2-3 días

2. Refactorizar para PWA
   - Remover props drilling
   - Agregar hooks de offline detection
   - Simplificar lifecycle (sin recovery hacky)
   - Tiempo: ~3-5 días

3. Layouts e integración
   - Main layout (AppContainer)
   - Toast/notification system
   - Modal manager
   - Tiempo: ~2-3 días

**Complejidad:** LOW-MEDIUM (copy-paste + refactor)  
**Riesgo:** LOW (código probado en proyecto actual)  
**Estimado:** 2-2.5 semanas

---

#### **Fase 3: Network + Real-time (1.5-2 semanas)**
1. Servicio de API (desde cero)
   ```typescript
   // services/api.ts
   export class APIClient {
     constructor(baseUrl, store) {
       this.baseUrl = baseUrl;
       this.store = store;
     }
     
     async request(method, path, data) {
       // Retry logic built-in
       // Offline queue built-in
       // Exponential backoff
     }
   }
   ```
   - Líneas: ~300-400
   - Cleanly designed, no legacy code

2. WebSocket con fallback
   ```typescript
   // services/gameSocket.ts
   export class GameSocket {
     constructor(baseUrl, userId, store) { }
     
     async connect(gameId) {
       try {
         // WS attempt
       } catch {
         // Fallback to polling
         this.startPolling(gameId);
       }
     }
   }
   ```
   - Líneas: ~200-300
   - Clear separation of concerns

3. Offline sync engine
   ```typescript
   // services/offlineSync.ts
   export class OfflineSync {
     async sync() {
       const queue = this.store.offlineQueue;
       for (const action of queue) {
         await this.execute(action);
       }
     }
   }
   ```
   - Líneas: ~150-200

**Complejidad:** MEDIUM (nueva arquitectura, pero limpia)  
**Riesgo:** LOW-MEDIUM (bien encapsulado)  
**Estimado:** 1.5-2 semanas

---

#### **Fase 4: Features (2-2.5 semanas)**
1. Authentication flow (~3-4 días)
   - Login/register pages
   - Token management
   - Session recovery

2. Lobby + Team management (~3-4 días)
   - Game creation
   - Roster selection
   - Team customization

3. Gameplay + Stadium (~5-7 días)
   - Real-time pitch/swing/tactic
   - Animations (Framer Motion)
   - Game over modal
   - Statistics display

4. Cards + Showcase (~2-3 días)
   - Card gallery
   - Team roster display
   - Filtering/sorting

**Complejidad:** MEDIUM (copy UI, refactor state)  
**Riesgo:** LOW (incrementalmental feature by feature)  
**Estimado:** 2-2.5 semanas

---

#### **Fase 5: Polish + Performance (1-1.5 semanas)**
1. Theming (Tailwind)
   - Koshien color scheme
   - Dark mode support
   - Responsive breakpoints

2. Audio (Web Audio API)
   - Copy audioManager.js from current project
   - Integrate with Zustand store

3. i18n (i18next)
   - Copy i18n.js
   - Integrate with stores

4. Performance optimization
   - Code splitting by route
   - Image optimization
   - Bundle analysis

**Estimado:** 1-1.5 semanas

---

#### **Fase 6: Testing (1 semana)**
1. Unit tests
   - Stores (Zustand)
   - Utilities
   - API client

2. Integration tests
   - Offline → Online flow
   - WebSocket → polling fallback
   - Queue sync

3. E2E tests
   - Login → Game → End
   - Offline gameplay

4. Manual testing
   - Multiple browsers
   - Slow network simulation
   - Offline mode

**Estimado:** 1 week

---

### **TOTAL START FROM SCRATCH: 6.5-9 semanas**

| Fase | Semanas | Riesgo | Complejidad |
|------|---------|--------|-------------|
| 1. Setup PWA + Arquitectura | 1 | LOW | MEDIUM |
| 2. Componentes + UI | 2-2.5 | LOW | LOW-MEDIUM |
| 3. Network + Real-time | 1.5-2 | LOW-MEDIUM | MEDIUM |
| 4. Features | 2-2.5 | LOW | MEDIUM |
| 5. Polish + Performance | 1-1.5 | LOW | LOW |
| 6. Testing | 1 | LOW | MEDIUM |
| **TOTAL** | **6.5-9** | **LOW-MEDIUM** | **MEDIUM** |

### Cambios de Archivo (Todo nuevo)

```
🆕 Crear: vite.config.ts (con vite-plugin-pwa)
🆕 Crear: src/main.tsx (React 18 con TS)
🆕 Crear: src/App.tsx (limpio, basado en stores)
🆕 Crear: src/stores/* (auth.ts, game.ts, ui.ts, offlineQueue.ts)
🆕 Crear: src/db/index.ts (Dexie schema)
🆕 Crear: src/services/* (api.ts, gameSocket.ts, offlineSync.ts)
🆕 Crear: src/components/* (reutilización de código actual + refactor)
🆕 Crear: src/pages/* (reutilización de código actual + refactor)
🆕 Crear: src/hooks/* (custom hooks, clean design)
🆕 Crear: public/manifest.json (vite-plugin-pwa lo genera)
🆕 Crear: public/sw.js (vite-plugin-pwa lo genera)
🆕 Crear: public/icons/*.png (diseño)
🆕 Crear: tests/* (unit, integration, e2e)

📁 Copiar del proyecto actual: 80% de componentes/lógica
```

### Riesgos Clave

1. **Reimplementación incompleta** → Olvidar features
2. **Architecture decisions** → Necesita consenso early
3. **Testing coverage** → Fácil de dejar para el final

### Ventajas del Start from Scratch

✅ **Arquitectura limpia desde día 1** → Zustand como core  
✅ **PWA nativa** → Service worker desde inicio  
✅ **Sin deuda técnica** → No hay código legacy que arrastrar  
✅ **Más rápido** → 6.5-9 semanas vs 9-11  
✅ **Fácil de debuggear** → Código nuevo, sin confusión  
✅ **Mejor performance** → PWA patterns desde cero  
✅ **TypeScript** → Mejor type safety (TS desde inicio)  

### Desventajas del Start from Scratch

❌ **Reimplementación** → Duración inicial  
❌ **Risk of missing features** → Necesita planning cuidadoso  
❌ **Testing burden** → Todo debe ser testeado  
❌ **Feature parity** → Validar que todo funciona igual

---

## 🎯 COMPARACIÓN DIRECTA

### Tiempo Total
| Opción | Semanas | Meses |
|--------|---------|-------|
| Conversión | 9-11 | 2.1-2.6 |
| Start from Scratch | 6.5-9 | 1.5-2.1 |
| **Diferencia** | **-2.5 a -2 semanas (23% más rápido)** | **-0.6 a -0.5 meses** |

### Riesgo de Bugs
| Opción | Riesgo | Razón |
|--------|--------|-------|
| Conversión | **HIGH** | Refactor masivo + deuda técnica |
| Start from Scratch | **MEDIUM** | Copy-paste seguro, architecture nuevo |

### Calidad Técnica
| Aspecto | Conversión | Start from Scratch |
|--------|-----------|-------------------|
| **Arquitectura** | Híbrida, confusa | Limpia, coherente |
| **Deuda técnica** | **Alta** (old + new mixed) | **Baja** (greenfield) |
| **Mantenibilidad** | **Difícil** (legacy patterns) | **Fácil** (nuevo, claro) |
| **Performance** | **Buena** (similar) | **Excelente** (PWA natives) |
| **Testing** | **Problemático** (mezcla) | **Fácil** (aislado) |

### ROI (Return on Investment)
```
Conversión:
  - Reutiliza 80% código → ahorra 1-2 semanas
  - Refactor masivo → suma 2-3 semanas
  - Total: 9-11 semanas
  - Resultado: App con deuda técnica
  - ROI BAJO

Start from Scratch:
  - Construir desde cero → 6.5-9 semanas
  - Copia inteligente de lógica probada → resta 1-2 semanas
  - Total: 6.5-9 semanas
  - Resultado: App limpia, mantenible, PWA-native
  - ROI ALTO
```

---

## 📋 RECOMENDACIÓN FINAL

### ✅ **RECOMENDACIÓN: START FROM SCRATCH**

**Razones:**

1. **30% más rápido** (6.5-9 semanas vs 9-11)
2. **Mejor arquitectura** (Zustand limpio vs props drilling)
3. **PWA-native** (service worker desde día 1 vs retrofit)
4. **Sin deuda técnica** (código nuevo vs mezcla old/new)
5. **Más mantenible** (futura expansión/features más fácil)
6. **TypeScript ready** (mejor type safety)
7. **Riesgo menor** (arquitectura clara, testing fácil)

### ❌ **NO RECOMENDADO: Conversión**

**Razones para evitar:**
1. Similar duración (9-11 vs 6.5-9 semanas)
2. Mayor riesgo de bugs (refactor masivo)
3. Tech debt híbrido (no limpia)
4. Zustand como "parche", no integración
5. Debugging más complejo
6. Menos beneficio a largo plazo

---

## 🧭 REGLAS DE DESARROLLO Y ESTÁNDARES DE CÓDIGO (PWA)

> Convenciones obligatorias para todo código de `pwa/`. Basadas en las mejores
> prácticas actuales de React + TypeScript, Vite + Tailwind, Zustand, pautas de
> accesibilidad (WCAG) y PWA (Google/Web Platform). Se respetan SIEMPRE, salvo
> decisión explícita y documentada.

### 1. TypeScript (escrito estricto desde el día 1)

| # | Regla |
|---|-------|
| 1.1 | `tsconfig.json` con `strict: true`, `noUncheckedIndexedAccess`, `noImplicitOverride`, `verbatimModuleSyntax` |
| 1.2 | Prohibido `any`. Para incógnitas usar `unknown` y estrechar antes de usar |
| 1.3 | Tipar SIEMPRE props, respuestas de API, parámetros y retornos de funciones |
| 1.4 | `import type { ... }` para imports que solo son tipos (con `verbatimModuleSyntax` es obligatorio) |
| 1.5 | Usar `interface` para objetos/contratos (Props, models) y `type` para uniones/alias (`type ID = string`) |
| 1.6 | Naming: `camelCase` variables/funciones/archivos helper; `PascalCase` componentes, tipos, interfaces y nombres de archivo de componentes |
| 1.7 | Constantes de dominio en `const` objetos con `as const` (o `enum` en `src/shared/constants`) — nunca magic strings en componentes |
| 1.8 | El lint (ESLint + `typescript-eslint` recomendado + react-hooks) y el build DEBEN quedar verdes antes de marcar cualquier tarea como completa |

### 2. Componentes React

| # | Regla |
|---|-------|
| 2.1 | Solo **functional components**. Prohibido class components |
| 2.2 | **Named exports** (`export function MyComponent`) para componentes; archivos `.tsx` en `PascalCase` |
| 2.3 | Props tipadas con `interface XProps { ... }` y se destructuran en la firma |
| 2.4 | Un componente = una responsabilidad (SRP). Si supera ~150 líneas o mezcla >2 preocupaciones, dividir |
| 2.5 | Composición sobre contexto/prop-drilling profundo: `<Card><Card.Body>…` antes que un componente todoterreno con 15 props |
| 2.6 | Subcomponentes privados: definir en el mismo archivo con `function` (module scope), no exportar si solo se usan ahí |
| 2.7 | Handlers con prefijo `on`/`handle` consistentes: prop `onChange`, controlador `handleZoneClick` |
| 2.8 | Derivar estado de UI en lugar de duplicarlo (p.ej. `isDisabled` = condición, no un booleano más en el store) |
| 2.9 | Botones/link reales: `<button>` y `<a href>`; prohibido `div onClick` para acciones interactivas |
| 2.10 | Contenedor (lógica/estado) separado de presentacional: páginas orquestan, componentes `shared/ui` solo renderizan reciben props |

### 3. Hooks

| # | Regla |
|---|-------|
| 3.1 | Cumplir las Rules of Hooks: solo en el nivel superior, solo en componentes/hooks, nunca condicionales ni en loops |
| 3.2 | Custom hooks con prefijo `use` y un solo propósito (p.ej. `useGameSocket`, `useOnlineStatus`) |
| 3.3 | Extraer efectos complejos a custom hooks; cada `useEffect` hace UNA cosa |
| 3.4 | Controlar dependencias: nunca desactivar warnings con `eslint-disable`; usar `useCallback`/`useMemo` cuando la referencia es dependencia de un efecto |
| 3.5 | Limpieza de efectos (unsubscribe/clearTimeout) SIEMPRE en el return del efecto |]

### 4. Estado global (Zustand)

| # | Regla |
|---|-------|
| 4.1 | Un store por feature (`features/<feature>/store.ts`), combinados en el root si hace falta (`shared/store`) |
| 4.2 | Estado = fuente de verdad única; el servidor no es el estado: los datos llegan por acciones/selectores |
| 4.3 | Mutaciones SIEMPRE vía acciones del store (`set`/`get`), nunca asignación directa a estado externo |
| 4.4 | Selectores en componentes: `useStore(useShallow(sel))` o selectores primitivos para evitar re-renders innecesarios |
| 4.5 | `persist` middleware para auth/sesión (localStorage); datos pesados de partida en IndexedDB (ver Fase 4) |
| 4.6 | No guardar estado derivado/inmutable repetido; derivar en selector o con `useMemo` |
| 4.7 | Tipar store con `interface XState` + acciones tipadas; acciones nombradas con verbo (`startGame`, `setPhase`) |

### 5. API / Network

| # | Regla |
|---|-------|
| 5.1 | Todo el HTTP por la instancia Axios central (`shared/api/client.ts`); prohibido `fetch` suelto en componentes |
| 5.2 | Interceptores gestionan JWT (cabecera `Authorization`), errores (traducción a `ApiError`) y retry con backoff |
| 5.3 | Cada endpoint tipado (`features/<f>/api.ts`): funciones `getX()/postX()` con tipos de request/response |
| 5.4 | Llamadas de red solo en capas de datos/hooks, NUNCA dentro de render |
| 5.5 | Errores de red: estado UI de loading/error por estado del store (patrón request/status), no `try/catch` crudo en cada página |
| 5.6 | Los endpoints mutantes (`pitch`, `swing`, `tactic`, `steal`, `ack`) pasan por la cola offline (Fase 4) |

### 6. Estilos (Tailwind) y diseño

| # | Regla |
|---|-------|
| 6.1 | Solo clases Tailwind; prohibido CSS ad-hoc o estilos inline salvo valores dinámicos (p.ej. posiciones del stats) |
| 6.2 | Colores del tema definidos en `tailwind.config` (paleta Koshien) y usados con tokens (`bg-primary`, `text-gold`) — nunca hex literales en componentes |
| 6.3 | Escala de espaciado tipográfica consistente (4px base); reutilizar breakpoints custom del proyecto (`xs`…`4k`) |
| 6.4 | Dark mode: tema con variantes `dark:` controlado por clase en `<html>` (agregado por el theme provider) |
| 6.5 | Móvil-first: diseñar para teléfonos y escalar con breakpoints ascendentes; probar mínimo en iPhone SE y pantallas grandes |
| 6.6 | `shared/ui` como design system: Button, Modal, Spinner, Toast con props consistentes y variantes (`variant`, `size`) |

### 7. Accesibilidad (a11y / WCAG AA)

| # | Regla |
|---|-------|
| 7.1 | Contraste de texto ≥ 4.5:1 (AA); verificar con el tema Koshien |
| 7.2 | `aria-label` en controles solo con icono; `role`/`aria-live` para zonas de estado (marcador, resultados) |
| 7.3 | `focus-visible` visible en todos los elementos interactivos |
| 7.4 | Navegación completa por teclado (Tab/Enter/Espace) en pitch zones y tácticas |
| 7.5 | HTML semántico: `button`, `main`, `header`, `dialog` (nativo o con `role="dialog"`) en modales |
| 7.6 | Título de página por ruta (`document.title`) y `lang` correcto en `index.html` |

### 8. Motion (Framer Motion)

| # | Regla |
|---|-------|
| 8.1 | Animaciones para estados clave (resultados de jugada, transición de inning), no para todo |
| 8.2 | **Respetar `prefers-reduced-motion`**: desactivar/aminorar con la variante global del proyecto |
| 8.3 | Duración corta (100–400ms) y curves suaves; sin animaciones que bloqueen el juego (WS) |
| 8.4 | `AnimatePresence` para montado/desmontado de modales/overlays, con foco devuelto al cerrar |

### 9. Reglas PWA (instalación + offline)

| # | Regla |
|---|-------|
| 9.1 | HTTPS obligatorio en producción (SW solo funciona en HTTPS/localhost) |
| 9.2 | manifest: `name`, `short_name` (≤12 chars), `theme_color` `#8B4513`, `background_color` `#121619`, `display` standalone, `start_url`, `orientation` portrait |
| 9.3 | Iconos: 192, 512 y `purpose: "maskable"` (con safe zone ≥80% del canvas) y `apple-touch-icon` 180 |
| 9.4 | Service worker (Workbox): **cache-first** para assets estáticos con hash; **network-first** para API; **stale-while-revalidate** no para mutaciones |
| 9.5 | Estrategias de actualización: flujo de `autoUpdate` en repo; si hay cambios, notificar y refrescar al usuario en el próximo `visibilitychange` |
| 9.6 | App shell cacheable para navegación offline; las mutaciones van a la cola de sync y se drenan al volver `online` |
| 9.7 | IndexedDB para datos >localStorage (estado de partida, historial); schema con versionado y migraciones (`offline/db.ts`) |
| 9.8 | Meta tags: `theme-color`, `apple-mobile-web-app-capable`, `viewport` con `viewport-fit=cover` y `env(safe-area-inset-*)` en botones/header |
| 9.9 | UI de instalación (`beforeinstallprompt`) sin trust-baiting; propuesta tras una intención clara del usuario |
| 9.10 | Monitorear instalación y actualización de SW en consola/devtools (Application → Service Workers) en cada verificación |

### 10. Performance

| # | Regla |
|---|-------|
| 10.1 | Code splitting por ruta obligatorio (`React.lazy` + `Suspense`); el stadium carga solo al entrar a `/game/:gameId` |
| 10.2 | Imágenes: formatos webp/avif, ≤150KB (ideal <100KB), `loading="lazy"`; comprimir los 3 fondos actuales (~10MB → <1MB c/u) |
| 10.3 | Evitar re-renders: selectores primitivos de Zustand, `React.memo` solo con causa medible, props estables |
| 10.4 | Budget de bundle: JS inicial ≤ 250KB gzip; auditoría con `vite build` + análisis en cada fase (2, 3, 5) |
| 10.5 | Monitorear Core Web Vitals en Lighthouse al cierre de cada fase (FCP, LCP, CLS, INP) |

### 11. Testing (Vitest/Testing Library + Playwright)

| # | Regla |
|---|-------|
| 11.1 | Unit (Vitest + Testing Library): stores, utils, API client, y lógica pura (event sequencer, normalizers) |
| 11.2 | Estructura: `describe('feature', ...)` → `it('debe ...' / 'should ...')` |
| 11.3 | Probar comportamiento, no implementación (eventos de usuario, no llamadas internas) |
| 11.4 | E2E (Playwright): login→onboarding→partida→game over, instalación PWA, fallo de red (offline→online) |
| 11.5 | Integration: WebSocket→polling fallback, drenado de cola offline, recuperación de sesión |
| 11.6 | Ninguna tarea/componente se da por cerrada sin su test mínimo (o justificación escrita) |

### 12. Git / Flujo de trabajo

| # | Regla |
|---|-------|
| 12.1 | Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:` (+ `breaking:`) |
| 12.2 | Commits atómicos y pequeños; UNA feature por PR; rama `main` protegida |
| 12.3 | Mensajes en Español o Inglés (elegir uno y mantenerlo); referencia al checklist de fases en el PR |
| 12.4 | Antes de commit: `npm run lint` + `npm run test` verdes (mismo criterio que el cierre de fase) |
| 12.5 | No commitear `dist/`, `.env*`, node_modules; `.gitignore` de TS/Vite actualizado |

### 13. Seguridad

| # | Regla |
|---|-------|
| 13.1 | Nunca exponer secretos en el cliente (cualquier string en el bundle es público) |
| 13.2 | El cliente valida UX; el servidor es la fuente de verdad (auth y reglas de negocio ya viven en backend) |
| 13.3 | JWT: mantener el modelo del backend actual; ante XSS, preferir `httpOnly` cookies si se migra el backend — documentar la decisión |
| 13.4 | Sanitizar/escapar antes de renderizar datos dinámicos; React ya lo hace por defecto — no usar `dangerouslySetInnerHTML` |
| 13.5 | CORS limitado a orígenes conocidos y credenciales configuradas explícitamente (backend actual) |

---

## 📋 CONTROL DE FASES (PWA) — CHECKLIST DE AVANCE

> **Cómo usar:** marca cada tarea `- [ ]` → `- [x]` conforme se finalice y actualiza
> la **Tabla de Estado** al completar cada fase entera. El backend NO se toca.
> **Criterio de cierre de fase:** `npm run build` + `npm run lint` + `npm run test` verdes
> y la verificación manual indicada en cada fase.

### Tabla de Estado

| Fase | Descripción | Estado |
|------|-------------|--------|
| 0 | Scaffold `pwa/` (Vite + React + TS estricto + Tailwind + Router) | [x] |
| 1 | Infraestructura core (API client, auth, i18n) | [ ] |
| 2 | Lobby + Team + Cards | [ ] |
| 3 | Game / Stadium (WebSocket + componentes) | [ ] |
| 4 | PWA + Offline (manifest, SW, IndexedDB, sync) | [ ] |
| 5 | Polish + Features restantes (shop, audio, i18n, perf) | [ ] |
| 6 | Testing + Deploy | [ ] |

---

### FASE 0 — Scaffold `pwa/` ✅ COMPLETADA

**Objetivo:** base reproducible y tipada antes de migrar cualquier lógica.

**Stack real usado:** React 19.2, Vite 8.2, TypeScript ~6.0, oxlint (nuevo estándar
de la plantilla), Tailwind CSS **v4** (config en CSS vía `@theme`, sin
`tailwind.config`), vitest 4.1, vite-plugin-pwa 1.3.

- [x] Crear `pwa/` dentro de `deck-at-the-plate/`: `npm create vite@latest pwa -- --template react-ts`
- [x] TS estricto en `tsconfig.app.json` (`strict`, `noUncheckedIndexedAccess`, `noImplicitOverride`, `verbatimModuleSyntax`, `noFallthroughCasesInSwitch`) — flag en el tsconfig de la app, no en el raíz (estructura de project references de la plantilla)
- [x] Instalar deps: `react-router-dom` 7, `zustand` 5, `axios`, `dexie` 4, `i18next` + `react-i18next`, `framer-motion` 13, `lucide-react`, `tailwindcss` 4 + `@tailwindcss/vite`, `vite-plugin-pwa`, `vitest` 4 + Testing Library
- [x] `vite.config.ts` con plugin React + Tailwind + PWA + alias `@/` → `src/` + `VITE_API_URL`/`VITE_WS_URL` tipadas en `vite-env.d.ts`
- [x] Tailwind con paleta Koshien + fonts (Teko, Courier Prime, Inter) migradas al tema `@theme` en `src/index.css` (breakpoints `xs`/`4k`, sombras scoreboard/vintage incluidas)
- [x] Lint: **oxlint** (sustituye a ESLint en la plantilla Vite 8; reglas react-rules-of-hooks + only-export-components) + **Prettier** (`.prettierrc.json`, singleQuote/semi off)
- [x] Vitest con test humo (`App.test.tsx` renderiza `/auth` — pasa)
- [x] Estructura feature-based: `src/app`, `src/features/{auth,lobby,team,game,cards}`, `src/shared/{api,ui,hooks,lib}`, `src/test`
- [x] `App.tsx` (componente) + `routes.tsx` (rutas con `React.lazy` + code splitting por página): `/auth`, `/lobby`, `/team`, `/roster/:gameId`, `/showcase`, `/game/:gameId`; lazy components en `app/lazyPages.ts`, router en `app/router.ts`
- [x] `providers.tsx` (provider root) + `shared/lib/i18n.ts` (ES/EN con detector de lenguaje)
- [x] Actualizar `docker-compose.yml` (servicio `pwa` en :5173 con `VITE_API_URL`/`VITE_WS_URL`) y crear `pwa/Dockerfile` (node:24-alpine)
- [x] **Verificación:** dev server HTTP 200 + HMR en :5173, `npm run lint` (0 warnings), `npm run typecheck`, `npm run test` (1/1), `npm run build` OK — index 107KB gzip (< 250KB budget), chunks por página, SW + manifest generados

**Salida:** App React tipada con router, stores vacíos, lint, test y build funcionando.

---

### FASE 1 — Infraestructura Core (API + Auth + i18n)

**Objetivo:** login de punta a punta contra el backend actual (`localhost:8000`).

- [ ] `shared/api/client.ts`: Axios instance con base URL desde env
- [ ] `shared/api/interceptors.ts`: inyección de JWT + retry con exponential backoff + error handler central
- [ ] `shared/api/types.ts`: tipos para respuestas del backend (LoginResponse, GameSessionResponse, etc.)
- [ ] `features/auth/store.ts`: Zustand con `persist` (user, token, login/logout) en localStorage
- [ ] `features/auth/api.ts`: `register()` y `login()`
- [ ] `features/auth/pages/AuthPage.tsx`: migrar `AuthScreen.jsx` (login + registro, validación)
- [ ] Ruta protegida (`<ProtectedRoute>` redirige a `/auth` sin token)
- [ ] i18n base: copiar `src/i18n.js` → `shared/lib/i18n.ts` (ES/EN, detector por localStorage)
- [ ] **Verificación:** registrarse, cerrar sesión, volver a loguear; token sobrevive refresh

---

### FASE 2 — Lobby + Team + Cards

**Objetivo:** navegación y gestión de equipo funcionales con datos reales.

- [ ] `features/lobby/store.ts`: config de partida (rival CPU, innings, difficulty)
- [ ] `features/lobby/api.ts`: `get_cpu_teams`, `create_game`
- [ ] `features/lobby/pages/LobbyPage.tsx`: migrar `LobbyScreen.jsx` (carrusel de franquicias, modos, settings)
- [ ] `features/team/store.ts` + `api.ts`: lineup, roster, `get_user_team`, `get_user_inventory`
- [ ] `features/team/pages/MyTeamPage.tsx`: migrar `MyTeamScreen.jsx` (roster + lineup)
- [ ] `features/team/pages/RosterSelectionPage.tsx`: migrar `RosterSelectionScreen.jsx` (lineup + deck táctico pre-partida)
- [ ] `features/cards/components/PlayerCard.tsx`: migrar `cards/PlayerCard.jsx` → TS con props tipadas
- [ ] `shared/ui/` design system mínimo: Button, Modal, Spinner, Toast (base)
- [ ] **Verificación:** flujo Auth → Onboarding (franquicia + starter pack) → Lobby → Team → Showcase

---

### FASE 3 — Game / Stadium (Core)

**Objetivo:** el gameplay 1v1 completo en tiempo real (migración del estadio).

- [ ] `features/game/store.ts`: Zustand (estado de partida, fase, marcador, current_pitch, runners)
- [ ] `features/game/services/socket.ts`: servicio WebSocket con **reconnect + backoff** y fallback a polling HTTP 2s
- [ ] `features/game/hooks/useGameSocket.ts`: suscribir store a eventos (PITCH_COMMITTED, PLAY_RESOLVED, STEAL_RESOLVED, PITCHER_CHANGED)
- [ ] Migrar `useEventSequencer.ts` (timing/animation orchestrator) → `features/game/hooks/`
- [ ] Migrar `useGameStatePersistence.ts` + `useGameRecovery.ts` (snapshot y recuperación de sesión)
- [ ] Migrar `features/game/components/stadium/*` al layout nuevo (GameplayInterface, CentralField, siluetas)
- [ ] Componentes de base: GameHeader, GameInfo, Scoreboard, ScoreboardHeader
- [ ] Picheo: `PitchSelector`, `PitchZoneGrid`, `StrikeZoneGrid` (humano y CPU)
- [ ] Estadísticas: GameStatsPanel, LineupPanel, PitcherStaminaBar, StrikeoutCounter
- [ ] Tácticas: TacticalHand, TacticalCardItem, SubmitPlayButton
- [ ] Modales: GameIntroModal, InningTransitionModal, PlayResultOverlay, GameOverModal, QuitGameModal
- [ ] Cambio de pitcher: ChangePitcherModal + RivalPitcherChangeModal (con ack y desbloqueo)
- [ ] `features/game/api.ts`: `pitch`, `swing`, `steal`, `play_tactic`, `change_pitcher`, `acknowledge`, box-score
- [ ] **Verificación:** partida PvE completa contra backend local (picheo→swing→táctica→robo→cambio de pitcher→fin)

---

### FASE 4 — PWA + Offline

**Objetivo:** instalable y funcional en modo offline con resync automático.

- [ ] `vite-plugin-pwa` con `registerType: 'autoUpdate'` y Workbox (precache build + runtime cache de API)
- [ ] manifest.json: name/short_name/theme_color `#8B4513`/background `#121619`, `display: standalone`
- [ ] Iconos: 192x192, 512x512, maskable (y apple-touch-icon 180)
- [ ] Meta tags en `index.html`: `theme-color`, `apple-mobile-web-app-capable`
- [ ] `offline/db.ts`: Dexie schema con versionado y migraciones (`gameState`, `gameHistory`, `userCards`, `roster`)
- [ ] `offline/sync.ts`: cola offline de acciones (pitch, swing, tactic, steal) + drenado al reconectar (`online` event)
- [ ] Persistir stores en IndexedDB (auth sigue en localStorage como fallback de sesión)
- [ ] Detección online/offline (`useOnlineStatus`) para UI de estado
- [ ] **Verificación:** `npm run preview` sobre HTTPS local → instalar en Chrome, recargar offline, jugar/JWT persisten

---

### FASE 5 — Polish + Features Restantes

**Objetivo:** feature parity con el frontend actual y calidad visual/performance.

- [ ] `features/shop/api.ts` + páginas: `claim_starter_pack`, `open_pack` (onboarding + tienda)
- [ ] Migrar `OnlineOnboarding`/`OnboardingScreen.jsx` (franquicia + apertura de pack) si no se hizo en Fase 2
- [ ] Migrar `audioManager.js` → `shared/lib/audio.ts` (Sintetizador Web Audio) e integrar con eventos del juego
- [ ] i18n completo de todas las pantallas (ES/EN toggle persistente)
- [ ] Theming: dark mode, breakpoints responsive (hasta iPhone SE y 4K), paleta Koshien verificada
- [ ] Performance: code splitting por ruta (`React.lazy`), precarga de modales del juego
- [ ] Optimizar imágenes: comprimir/re-dimensionar `stadium`, `playbal`, `lineup` (<1MB cada una ideal)
- [ ] **Verificación:** Lighthouse PWA ≥ 90/100, bundle split cargado bajo demanda

---

### FASE 6 — Testing + Deploy

**Objetivo:** blindar calidad y desplegar la PWA al mismo origen que el backend.

- [ ] Unit: stores (Zustand), utils, API client, event sequencer (~tabla de eventos del backend)
- [ ] Integration: offline→online (drenado de cola), WebSocket→polling fallback, sesión recuperada
- [ ] E2E (Playwright): login→onboarding→partida→game over; instalación PWA; shutdown de red
- [ ] Pruebas manuales: Chrome/Safari/Edge, red lenta (Throttling), modo avión, instalación a home screen
- [ ] Servir build estático desde el backend (DOCROOT en FastAPI) o contenedor separado en el mismo dominio → WS/API same-origin
- [ ] Env de producción: HTTPS, `VITE_API_URL` relativo, cache headers (max-age hashes, no-cache manifest/sw)
- [ ] Actualizar `docker-compose.yml`/CI para build de `pwa/` en el flujo
- [ ] **Verificación:** instalación limpia + partida PvE completa en producción, Lighthouse PWA/Performance verdes

---

### Post-Launch: Monitoring (opcional)

- [ ] Analytics: PWA installs, offline usage, sessions recuperadas
- [ ] Performance monitoring en campo (Core Web Vitals)
- [ ] Bug fixes iterativos con el checklist de regresión de partida

---

## 📊 APÉNDICE: Desglose Detallado de Líneas de Código

### Conversión (9-11 semanas)
```
Service Worker (sw.js): 400-500 líneas
Zustand stores: 600-700 líneas
IndexedDB (Dexie): 200-300 líneas
Offline queue: 200-300 líneas
Component refactoring: 1000-1500 líneas (50+ components)
API wrapper: 200-300 líneas
Manifest + config: 100-150 líneas
Tests: 500-700 líneas
─────────────────────────────
TOTAL: ~4000-5000 líneas netas
```

### Start from Scratch (6.5-9 semanas)
```
Vite config + PWA plugin: 200 líneas
Zustand stores (clean): 600-700 líneas
Dexie schema: 200-300 líneas
API client + services: 500-700 líneas
Components (copy+refactor): 1500-2000 líneas
Pages: 800-1000 líneas
Hooks: 300-400 líneas
Types: 300-400 líneas
Tests: 600-800 líneas
─────────────────────────────
TOTAL: ~5500-7000 líneas (clean, organized)
```

---

**Conclusión:** Start from Scratch es más rápido, más limpio, y sienta mejores bases para el futuro.

