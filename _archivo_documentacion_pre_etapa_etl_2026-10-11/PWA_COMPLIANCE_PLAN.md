# Plan de cumplimiento PWA

Documento operativo para llevar el proyecto `pwa/` al cumplimiento de las reglas definidas en `pwa_analysis.md`.

> `pwa_analysis.md` es la especificación. Este archivo es el tablero de ejecución y debe actualizarse al cerrar cada tarea.

## Cómo usar este plan

Estados permitidos:

- `PENDIENTE`: no iniciada.
- `EN CURSO`: trabajo activo.
- `BLOQUEADA`: existe una dependencia o decisión pendiente.
- `EN REVISIÓN`: implementación terminada, falta validación.
- `COMPLETA`: cumple todos sus criterios de aceptación y tiene evidencia.

Prioridades:

- `P0`: bloquea compilación, pruebas o entrega.
- `P1`: requisito esencial de PWA, seguridad, accesibilidad u operación offline.
- `P2`: arquitectura, rendimiento o experiencia importante.
- `P3`: mejora y mantenimiento.

Reglas de seguimiento:

1. Mover solamente una tarea a `EN CURSO` por frente de trabajo.
2. Registrar los archivos modificados y las decisiones relevantes en la tarea.
3. Una tarea solo pasa a `COMPLETA` cuando todos sus criterios de aceptación se cumplen.
4. Añadir como evidencia los comandos ejecutados, resultados, capturas o mediciones y el hash del commit.
5. Mantener los commits pequeños y enfocados, idealmente uno por tarea o por grupo inseparable.
6. Antes de cerrar cada fase deben pasar `lint`, `typecheck`, `test` y `build`.

## Línea base

Fecha del análisis: **2026-09-04**

| Comprobación | Estado inicial | Resultado |
| --- | --- | --- |
| `npm run lint` | Parcial | Termina correctamente, pero conserva advertencias de React y variables sin uso. |
| `npm run typecheck` | Falla | Errores en pruebas de Stadium y acceso potencialmente indefinido en Lobby. |
| `npm run test` | Falla | 72 de 83 pruebas pasan; 11 fallan. |
| `npm run build` | Falla | Bloqueado por los errores de TypeScript. |
| Manifest/installability | Parcial | Existe manifest y service worker, pero faltan metadatos e iconos requeridos. |
| Offline | Parcial | Hay precache, pero no persistencia IndexedDB, cola de mutaciones ni estrategia completa de sincronización. |
| Accesibilidad | Parcial | Hay bases útiles, pero faltan semántica y manejo de foco en diálogos, anuncios y validación manual. |
| Rendimiento | En riesgo | JavaScript inicial aceptable; imágenes y precache son demasiado pesados. |

## Resumen de avance

| Fase | Total | Completas | Estado |
| --- | ---: | ---: | --- |
| 0. Estabilización | 5 | 5 | COMPLETA |
| 1. Instalación PWA | 4 | 3 | EN REVISIÓN |
| 2. Persistencia y offline | 5 | 5 | COMPLETA |
| 3. Service worker | 4 | 4 | COMPLETA |
| 4. Rendimiento | 4 | 3 | EN CURSO |
| 5. Accesibilidad y movimiento | 6 | 4 | EN CURSO |
| 6. Arquitectura y estilos | 7 | 0 | PENDIENTE |
| 7. Cobertura de pruebas | 5 | 0 | PENDIENTE |
| 8. Validación y documentación | 5 | 0 | PENDIENTE |
| **Total** | **45** | **24** | **EN CURSO** |

---

## Fase 0 — Estabilización de calidad

### QLT-001 — Corregir configuración y ubicación de pruebas de Stadium

- Prioridad: `P0`
- Estado: `COMPLETA`
- Dependencias: ninguna
- Alcance: `StadiumPage.crossbrowser.test.ts`, `StadiumPage.css.test.ts`, configuración TypeScript/Vitest.
- Criterios de aceptación:
  - Las pruebas no dependen de globales Node sin tipos (`fs`, `path`, `__dirname`).
  - No hay variables sin uso, `implicit any` ni accesos posiblemente indefinidos.
  - Los archivos temporales o pruebas experimentales no rompen el código de producción.
  - `npm run typecheck` puede continuar sin errores provenientes de estas pruebas.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/tsconfig.app.json`
  - `pwa/src/features/game/pages/StadiumPage.css.test.ts`
  - `pwa/src/features/game/pages/StadiumPage.crossbrowser.test.ts`
- Evidencia:
  - `npm run typecheck`: las pruebas de Stadium ya no generan errores; tras completar `QLT-002`, el comando completo termina con código 0.
  - Pruebas específicas: 50 de 60 pasan; las 10 expectativas visuales obsoletas o pendientes se trasladan a `QLT-004`.
  - Se sustituyeron `fs`, `path` y `__dirname` globales por imports tipados `node:*` y una ruta resuelta desde el directorio del proyecto.

### QLT-002 — Corregir acceso inseguro al primer rival en Lobby

- Prioridad: `P0`
- Estado: `COMPLETA`
- Dependencias: ninguna
- Alcance: `pwa/src/features/lobby/pages/LobbyPage.tsx`.
- Criterios de aceptación:
  - No se accede a `teams[0].id` si la colección está vacía.
  - El estado vacío tiene una presentación y comportamiento definidos.
  - TypeScript no reporta el valor como posiblemente indefinido.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/features/lobby/pages/LobbyPage.tsx`
  - `pwa/src/shared/lib/i18n.ts`
- Evidencia:
  - `npm run typecheck`: termina con código 0.
  - El primer rival se obtiene mediante una guarda explícita antes de acceder a su ID.
  - Una lista vacía muestra un mensaje localizado y ya no permanece en carga indefinida.

### QLT-003 — Estabilizar pruebas del store de autenticación

- Prioridad: `P0`
- Estado: `COMPLETA`
- Dependencias: ninguna
- Alcance: configuración de Vitest y pruebas del store de autenticación.
- Criterios de aceptación:
  - `localStorage` está disponible o se sustituye con un mock aislado y reiniciable.
  - Las pruebas no comparten estado persistido entre casos.
  - Todas las pruebas del store de autenticación pasan de forma determinista.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/test/setup.ts`
- Evidencia:
  - `npm run test -- src/features/auth/store.test.ts`: 2 de 2 pruebas aprobadas.
  - `npm run typecheck`: termina con código 0.
  - El almacenamiento en memoria se instala antes de importar los stores y se limpia antes de cada prueba.

### QLT-004 — Resolver advertencias funcionales de lint

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: ninguna
- Alcance: `PlayResultOverlay`, `FloatingParticles`, `StadiumPage` y pruebas relacionadas, incluidas las expectativas CSS obsoletas detectadas en `QLT-001`.
- Criterios de aceptación:
  - No se ejecuta un `setState` síncrono innecesario dentro de efectos.
  - No se utiliza `Math.random()` durante renderizado.
  - No se lee o modifica una referencia de React durante renderizado de forma insegura.
  - No quedan advertencias de variables sin uso dentro del alcance.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/features/game/components/modals/PlayResultOverlay.tsx`
  - `pwa/src/features/game/hooks/useGameSocket.ts`
  - `pwa/src/features/game/pages/StadiumPage.tsx`
  - `pwa/src/features/game/pages/StadiumPage.module.css`
  - `pwa/src/features/game/pages/StadiumPage.css.test.ts`
  - `pwa/src/features/game/pages/StadiumPage.crossbrowser.test.ts`
  - `pwa/src/features/onboarding/components/FloatingParticles.tsx`
- Evidencia:
  - `npm run lint`: termina sin errores ni advertencias.
  - Pruebas CSS de Stadium: 60 de 60 aprobadas.
  - El overlay conserva un único resultado temporizado y no actualiza estado sincrónicamente al desmontarse.
  - Las partículas se generan de forma pura y determinista.
  - El socket entrega explícitamente el estado anterior para el snapshot visual, sin leer refs durante render.
  - La animación del contador respeta `prefers-reduced-motion`.

### QLT-005 — Recuperar pipeline local verde

- Prioridad: `P0`
- Estado: `COMPLETA`
- Dependencias: `QLT-001`, `QLT-002`, `QLT-003`, `QLT-004`
- Criterios de aceptación:
  - `npm run lint` termina sin errores ni advertencias relevantes.
  - `npm run typecheck` termina con código 0.
  - `npm run test` termina con todas las pruebas aprobadas.
  - `npm run build` genera el artefacto de producción.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos verificados: todo `pwa/`.
- Evidencia:
  - `npm run lint`: código 0, sin advertencias.
  - `npm run typecheck`: código 0.
  - `npm run test`: 6 archivos y 83 de 83 pruebas aprobadas.
  - `npm run build`: build de producción generado correctamente con Vite 8.2.2.
  - JavaScript inicial: 110.91 kB gzip.
  - Hallazgo trasladado a `PERF-001` y `SW-002`: precache actual de 41 entradas y 13,555.47 KiB.

---

## Fase 1 — Instalación PWA y metadatos

### PWA-001 — Completar el manifest

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - `short_name` tiene un máximo de 12 caracteres.
  - Se define la orientación requerida por la especificación.
  - Se conservan `start_url`, `display: standalone`, `theme_color` y `background_color` correctos.
  - El manifest generado pasa la validación de DevTools/Lighthouse.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/vite.config.ts`
- Evidencia:
  - `npm run build`: genera correctamente `dist/manifest.webmanifest`.
  - Manifest generado con `short_name: "Deck"`, `orientation: "portrait-primary"`, `display: "standalone"`, `start_url: "/"` y los colores requeridos.
  - La validación completa de instalación en navegadores permanece en `PWA-004`.

### PWA-002 — Generar iconos completos y maskable

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: ninguna
- Criterios de aceptación:
  - Existen iconos PNG válidos de 192×192 y 512×512.
  - Existe al menos un icono 512×512 con propósito `maskable` y zona segura verificada.
  - Existe `apple-touch-icon` de 180×180.
  - No se reutilizan imágenes que pierdan legibilidad al recortarse.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/public/icons/icon-180.png`
  - `pwa/public/icons/icon-192.png`
  - `pwa/public/icons/icon-512.png`
  - `pwa/public/icons/icon-maskable-192.png`
  - `pwa/public/icons/icon-maskable-512.png`
  - `pwa/vite.config.ts`
- Evidencia:
  - `file public/icons/*.png`: confirma dimensiones y formato PNG de las cinco imágenes.
  - `npm run build`: el manifest contiene variantes `any` y `maskable` de 192×192 y 512×512.
  - Las variantes maskable usan fondo opaco `#121619` y mantienen el emblema dentro del 75% central del canvas.

### PWA-003 — Completar metadatos para iOS y viewport

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `PWA-002`
- Criterios de aceptación:
  - `index.html` enlaza el `apple-touch-icon`.
  - Incluye metadatos Apple necesarios para ejecución standalone.
  - Mantiene `viewport-fit=cover` y usa safe-area cuando corresponde.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/index.html`
- Evidencia:
  - `npm run build`: termina con código 0.
  - `dist/index.html` conserva `viewport-fit=cover`, `apple-touch-icon` 180×180 y los metadatos de ejecución standalone para Apple.
  - La interfaz ya usa safe-area en autenticación, onboarding y notificaciones; la validación integral por dispositivo permanece en `PWA-004`.

### PWA-004 — Validar instalación en navegadores objetivo

- Prioridad: `P1`
- Estado: `EN REVISIÓN`
- Dependencias: `PWA-001`, `PWA-002`, `PWA-003`, `SW-003`
- Criterios de aceptación:
  - La aplicación es instalable en Chrome/Edge de escritorio y Android.
  - Se valida el comportamiento Add to Home Screen en Safari iOS.
  - Inicio desde icono abre la ruta y presentación esperadas.
- Evidencia parcial:
  - Manifest, iconos, registro en modo prompt y flujo `beforeinstallprompt` se validan mediante build y pruebas automatizadas.
  - `PwaInstallPrompt` detecta modo standalone y evita volver a sugerir instalación.
  - Pendiente para completar: validación manual en Chrome/Edge de escritorio, Android y Safari iOS sobre dispositivos objetivo.

---

## Fase 2 — Persistencia y funcionamiento offline

### OFF-001 — Definir e implementar esquema IndexedDB con Dexie

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - Existe un módulo dedicado en `src/offline/`.
  - El esquema tiene versión explícita y stores para los datos persistentes requeridos.
  - Las credenciales sensibles no se almacenan en IndexedDB.
  - Hay pruebas unitarias del esquema y operaciones básicas.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/offline/db.ts`
  - `pwa/src/offline/db.test.ts`
  - `pwa/src/test/setup.ts`
  - `pwa/package.json`
  - `pwa/package-lock.json`
- Evidencia:
  - Dexie usa `DATABASE_VERSION = 1` y crea `gameState`, `gameHistory`, `userCards` y `roster` con claves e índices explícitos.
  - No existen tablas de autenticación, tokens o credenciales.
  - `fake-indexeddb` se usa exclusivamente como dependencia de desarrollo.
  - Pruebas específicas: 3 de 3 aprobadas con apertura, escritura, lectura y transacción real.
  - Pipeline completo: lint y typecheck limpios, 86 de 86 pruebas aprobadas y build exitoso.

### OFF-002 — Migrar el estado de juego persistente desde localStorage

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `OFF-001`
- Criterios de aceptación:
  - El estado de juego que requiere persistencia usa IndexedDB.
  - La migración conserva datos existentes válidos o documenta su descarte seguro.
  - `localStorage` queda limitado a preferencias pequeñas y no sensibles.
  - Se prueban actualización de versión y migración.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/features/game/lib/persistence.ts`
  - `pwa/src/features/game/lib/persistence.test.ts`
  - `pwa/src/features/game/hooks/useGameSocket.ts`
  - `pwa/src/features/game/hooks/useGamePersistence.ts`
  - `pwa/src/shared/lib/sessionCleanup.ts`
- Evidencia:
  - El estado pesado de cada partida se almacena en `gameState` mediante una clave compuesta por partida y usuario; `localStorage` queda reservado para los identificadores ligeros de sesión y el estado de la introducción.
  - Una sesión válida de la implementación anterior se migra automáticamente a IndexedDB y sus claves antiguas se eliminan; una sesión de otro usuario o partido se descarta de forma segura.
  - `current_pitch` se elimina tanto al persistir como al recuperar datos legados para no conservar información transitoria o secreta del lanzamiento.
  - Pruebas específicas: 4 de 4 aprobadas para persistencia, aislamiento, migración y limpieza; junto con las 3 pruebas de versión/esquema de `OFF-001`, 7 de 7 aprobadas.
  - Pipeline completo: lint y typecheck limpios, 90 de 90 pruebas aprobadas y build de producción exitoso.

### OFF-003 — Implementar cola de mutaciones offline

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `OFF-001`
- Criterios de aceptación:
  - Las mutaciones soportadas se guardan con ID, payload, fecha, reintentos y estado.
  - La cola se drena al recuperar conexión sin duplicar operaciones.
  - Hay backoff y límite de reintentos.
  - Los errores permanentes son visibles y recuperables por el usuario.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados hasta ahora:
  - `pwa/src/offline/db.ts`
  - `pwa/src/offline/db.test.ts`
  - `pwa/src/offline/mutationQueue.ts`
  - `pwa/src/offline/mutationQueue.test.ts`
  - `pwa/src/offline/sync.ts`
  - `pwa/src/offline/sync.test.ts`
  - `pwa/src/offline/OfflineSyncStatus.tsx`
  - `pwa/src/features/team/rosterStore.ts`
  - `pwa/src/features/team/pages/MyTeamPage.tsx`
  - `pwa/src/app/providers.tsx`
  - `pwa/src/shared/lib/i18n.ts`
- Evidencia:
  - El esquema IndexedDB sube a versión 2 e incorpora `offlineMutations` con ID, usuario, operación, clave de deduplicación, payload, fechas, intentos, límite, próximo intento, estado y último error.
  - La cola reemplaza una mutación pendiente equivalente con el último estado deseado, evitando reproducir lineups obsoletos.
  - El drenado elimina operaciones exitosas, aplica backoff exponencial acotado y conserva errores definitivos en estado recuperable.
  - `lineup.save` funciona offline-first, conserva inmediatamente la edición en pantalla y comunica que quedó pendiente sin afirmar que el servidor ya la guardó.
  - La cola se drena al montar la aplicación y al recuperar conexión; si un reintento falla, se programa automáticamente según `nextAttemptAt` y solo se procesan operaciones del usuario autenticado.
  - Los fallos definitivos quedan visibles en una región accesible global y el usuario dispone de una acción para reintentarlos.
  - Las mutaciones dependientes del turno (`pitch`, `swing`, tácticas, robos y creación de partidas) no se encolan porque reproducirlas sobre un estado posterior no es seguro.
  - Pruebas específicas de IndexedDB, cola e integración de lineup: 10 de 10 aprobadas.
  - Pipeline completo: lint y typecheck limpios, 97 de 97 pruebas aprobadas y build PWA exitoso.

### OFF-004 — Definir conflicto y resincronización

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `OFF-003`
- Criterios de aceptación:
  - La estrategia de autoridad servidor/cliente está documentada por operación.
  - Los conflictos no sobrescriben silenciosamente datos más recientes.
  - Tras reconexión se refresca el estado autoritativo relevante.
  - Hay pruebas para duplicados, orden y conflicto.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/offline/README.md`
  - `pwa/src/offline/sync.ts`
  - `pwa/src/offline/sync.test.ts`
  - `pwa/src/offline/mutationQueue.ts`
  - `pwa/src/offline/mutationQueue.test.ts`
  - `pwa/src/offline/OfflineSyncStatus.tsx`
  - `pwa/src/features/team/rosterStore.ts`
- Evidencia:
  - La matriz de operaciones documenta autoridad, soporte offline y resolución para lineup, estado de juego, acciones por turno y operaciones que crean recursos.
  - `lineup.save` conserva la línea base confirmada, consulta el estado remoto antes de escribir y detiene la operación si detecta un cambio concurrente.
  - Si el servidor ya contiene el lineup deseado, la operación se considera idempotente y no repite el `PUT`.
  - Después de aplicar o detectar un conflicto se vuelve a consultar el lineup autoritativo; el usuario puede reintentar o descartar el cambio fallido.
  - Las pruebas cubren deduplicación, orden secuencial, aislamiento por usuario, estado ya aplicado, conflicto remoto, reintento y descarte.
  - Pipeline completo: lint y typecheck limpios, 100 de 100 pruebas aprobadas y build PWA exitoso.

### OFF-005 — Añadir estado de conectividad en la interfaz

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `OFF-003`, `OFF-004`
- Criterios de aceptación:
  - La interfaz anuncia modo offline, reconexión y sincronización pendiente.
  - Los controles no disponibles explican el motivo.
  - Los cambios de estado se anuncian mediante una región accesible.
  - La experiencia no depende exclusivamente del color.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/offline/OfflineSyncStatus.tsx`
  - `pwa/src/offline/OnlineRequiredHint.tsx`
  - `pwa/src/offline/useOnlineStatus.ts`
  - `pwa/src/offline/connectivity.test.tsx`
  - `pwa/src/features/auth/pages/AuthPage.tsx`
  - `pwa/src/features/lobby/pages/LobbyPage.tsx`
  - `pwa/src/features/onboarding/pages/OnboardingPage.tsx`
  - `pwa/src/features/team/pages/RosterSelectionPage.tsx`
  - `pwa/src/shared/lib/i18n.ts`
- Evidencia:
  - La región global `aria-live` anuncia desconexión, reconexión, sincronización, cambios pendientes y fallos mediante texto, sin depender exclusivamente del color.
  - Login/registro, creación de club, reclamación del sobre, avance al roster e inicio de partida quedan desactivados offline y enlazados mediante `aria-describedby` a una explicación visible.
  - El guardado del lineup permanece disponible offline porque cuenta con cola, deduplicación y resolución de conflictos.
  - Los handlers críticos también verifican conectividad para cubrir envíos de formulario por teclado o llamadas programáticas.
  - Las pruebas de interfaz verifican los eventos `online`/`offline`, la explicación contextual y el anuncio de reconexión.
  - Pipeline completo: lint y typecheck limpios, 103 de 103 pruebas aprobadas y build PWA exitoso.

---

## Fase 3 — Service worker y ciclo de actualización

### SW-001 — Configurar estrategias de runtime caching

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - APIs de lectura usan una estrategia compatible con frescura y tolerancia offline.
  - Recursos estáticos usan estrategias, expiración y límites definidos.
  - Respuestas privadas o mutaciones no se cachean de forma insegura.
  - Las reglas quedan documentadas y probadas.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/workbox.config.ts`
  - `pwa/workbox.config.test.ts`
  - `pwa/vite.config.ts`
  - `pwa/src/offline/README.md`
- Evidencia:
  - Las lecturas públicas permitidas (`teams/cpu` y detalle de carta) usan Network First con timeout de 4 segundos, respuestas HTTP 200, máximo de 60 entradas y expiración de 1 hora.
  - Imágenes y fuentes solicitadas en runtime usan Cache First con límites de 80/30 días y 12/1 año, respectivamente, además de purga por cuota.
  - Perfil, inventario, lineup, equipo, partidas y cualquier mutación quedan fuera de Cache Storage; no existe ninguna ruta Workbox para POST, PUT, PATCH o DELETE.
  - Las reglas y su justificación están documentadas en `src/offline/README.md`.
  - Tres pruebas unitarias verifican rutas públicas, exclusión de datos privados/mutaciones y límites de recursos estáticos.
  - Se inspeccionó el `dist/sw.js` final para confirmar que los matchers serializados son autocontenidos y no contienen referencias externas indefinidas.
  - Pipeline completo: lint y typecheck limpios, 106 de 106 pruebas aprobadas y build PWA exitoso.

### SW-002 — Definir precache y fallback offline

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `PERF-001`
- Criterios de aceptación:
  - El precache excluye recursos innecesarios o excesivamente pesados.
  - Existe un fallback de navegación coherente.
  - Los recursos esenciales de la experiencia inicial están disponibles offline.
  - El tamaño final del precache queda registrado.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/workbox.config.ts`
  - `pwa/workbox.config.test.ts`
  - `pwa/vite.config.ts`
  - `pwa/src/offline/README.md`
- Evidencia:
  - El precache conserva `index.html`, bundles con hash, manifest, favicon, iconos instalables, logo compacto y fondos AVIF esenciales.
  - Se excluyen variantes PNG pesadas de los fondos, `logo.png`, archivos de sistema y una imagen suelta no utilizada; los PNG de compatibilidad siguen disponibles por red y cache runtime bajo demanda.
  - Las navegaciones offline usan `/index.html` para permitir que React Router resuelva rutas internas.
  - `/api/` está en `navigateFallbackDenylist`, evitando devolver HTML en lugar de JSON.
  - La salida de Workbox bajó de 59 entradas / 14,963.06 KiB a 50 entradas / 2,411.13 KiB: aproximadamente 84% menos.
  - Se inspeccionó `dist/sw.js` para comprobar inclusiones esenciales, exclusiones y la ruta de navegación con denylist.
  - Pipeline completo: lint y typecheck limpios, 107 de 107 pruebas aprobadas y build PWA exitoso.

### SW-003 — Implementar notificación y aplicación de actualizaciones

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `SW-001`, `SW-002`
- Criterios de aceptación:
  - La interfaz informa cuando existe una nueva versión.
  - El usuario puede actualizar de forma controlada sin perder una operación activa.
  - Se contempla revalidación al volver a una pestaña visible.
  - El flujo de actualización está probado.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/vite.config.ts`
  - `pwa/src/vite-env.d.ts`
  - `pwa/src/app/providers.tsx`
  - `pwa/src/offline/PwaUpdatePrompt.tsx`
  - `pwa/src/offline/PwaUpdatePrompt.test.tsx`
  - `pwa/src/offline/updatePolicy.ts`
  - `pwa/src/offline/updatePolicy.test.ts`
  - `pwa/src/shared/lib/i18n.ts`
- Evidencia:
  - El registro cambia de `autoUpdate` a `prompt`; una versión en espera solo recibe `SKIP_WAITING` después de la acción explícita del usuario.
  - El aviso explica que existe una nueva versión y permite actualizar o posponerla.
  - La actualización queda bloqueada durante una partida activa o mientras haya mutaciones pendientes/procesándose, con una explicación accesible vinculada al botón.
  - Al volver la pestaña a estado visible se ejecuta `ServiceWorkerRegistration.update()` para revalidar la versión.
  - Las pruebas verifican política segura, aplicación controlada, bloqueo durante gameplay y revalidación por visibilidad.
  - Se inspeccionó el build para confirmar el listener `SKIP_WAITING` y el flujo de registro en modo prompt.
  - Pipeline completo: lint y typecheck limpios, 113 de 113 pruebas aprobadas y build PWA exitoso; precache de 50 entradas / 2,420.38 KiB.

### SW-004 — Añadir experiencia de instalación

- Prioridad: `P2`
- Estado: `COMPLETA`
- Dependencias: `PWA-001`, `PWA-002`, `PWA-003`
- Criterios de aceptación:
  - Se maneja `beforeinstallprompt` cuando está disponible.
  - La sugerencia no interrumpe tareas críticas y puede descartarse.
  - En iOS se muestran instrucciones específicas solo cuando aplican.
  - Se evita mostrar la invitación si la app ya está instalada.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/app/RootLayout.tsx`
  - `pwa/src/offline/PwaInstallPrompt.tsx`
  - `pwa/src/offline/PwaInstallPrompt.test.tsx`
  - `pwa/src/offline/installPolicy.ts`
  - `pwa/src/offline/installPolicy.test.ts`
  - `pwa/src/shared/lib/i18n.ts`
- Evidencia:
  - `beforeinstallprompt` se conserva y solo se ejecuta después de pulsar “Instalar”; `appinstalled` y los modos standalone ocultan futuras invitaciones.
  - La decisión “Ahora no” se conserva como preferencia local y evita interrupciones repetidas.
  - Safari en iPhone/iPad recibe instrucciones específicas; Chrome, Firefox y Edge en iOS quedan excluidos de esas instrucciones.
  - La invitación solo aparece en `auth`, `lobby`, `team` y `showcase`; queda suprimida en onboarding, roster, gameplay y durante cualquier partida activa.
  - Las pruebas cubren prompt nativo, aceptación, descarte persistente, standalone, navegadores iOS y rutas críticas.
  - Pipeline completo: lint y typecheck limpios, 119 de 119 pruebas aprobadas y build PWA exitoso; precache de 50 entradas / 2,423.48 KiB.

---

## Fase 4 — Rendimiento

### PERF-001 — Optimizar imágenes y fondos pesados

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: ninguna
- Hallazgo inicial: hay PNG aproximados entre 1.4 MB y 2.5 MB y un precache superior a 13 MB.
- Criterios de aceptación:
  - Imágenes grandes se convierten a WebP/AVIF cuando sea compatible.
  - Existen tamaños responsivos para fondos y contenido relevante.
  - No se reduce perceptiblemente la calidad visual necesaria.
  - Se documentan pesos antes/después y ahorro total.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/public/login-background.avif`
  - `pwa/public/stadium-desktop.avif`
  - `pwa/public/stadium-mobile.avif`
  - `pwa/public/start-desktop.avif`
  - `pwa/public/start-mobile.avif`
  - `pwa/public/open-pack.avif`
  - `pwa/public/open-pack-mobile.avif`
  - `pwa/src/index.css`
  - `pwa/src/features/game/pages/StadiumPage.module.css`
  - `pwa/src/features/game/components/modals/GameIntroModal.tsx`
- Evidencia:
  - Los siete PNG originales suman 8.04 MiB; sus variantes AVIF suman 0.39 MiB, una reducción aproximada de 95% para navegadores compatibles.
  - Los fondos conservan variantes móvil/escritorio y fallback PNG mediante `image-set`.
  - Las variantes AVIF preservan dimensiones, composición y apariencia de las fuentes originales.
  - `npm run lint`, `npm run typecheck`, `npm run test` (83/83) y `npm run build` terminan correctamente.
  - El precache aún incluye originales y variantes; su exclusión selectiva queda registrada en `SW-002`.

### PERF-002 — Revisar carga y cache de tipografías

- Prioridad: `P2`
- Estado: `COMPLETA`
- Dependencias: `SW-001`
- Criterios de aceptación:
  - Las tipografías críticas no bloquean indefinidamente el contenido.
  - Se define `font-display` apropiado.
  - Cache y origen de fuentes quedan explícitos.
  - Se evita descargar variantes no utilizadas.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/index.html`
  - `pwa/fontLoading.test.ts`
  - `pwa/workbox.config.ts`
  - `pwa/workbox.config.test.ts`
  - `pwa/src/offline/README.md`
- Evidencia:
  - La hoja de Google Fonts se precarga como estilo y se activa en `onload`, por lo que no bloquea el primer render; existe fallback `<noscript>`.
  - La URL conserva `display=swap`, permitiendo mostrar inmediatamente las familias del sistema mientras llegan las fuentes web.
  - Se eliminó Courier Prime itálica 400 porque no existe ningún uso itálico; permanecen únicamente Courier Prime 400/700, Inter 400/600/700 y Teko 600/700.
  - El CSS de `fonts.googleapis.com` usa Stale While Revalidate con 6 entradas/30 días; los archivos de `fonts.gstatic.com` usan Cache First con 12 entradas/1 año.
  - Preconnect, orígenes, estrategias y límites quedan explícitos y documentados.
  - Se inspeccionó `dist/sw.js` para confirmar que ambos orígenes y caches se serializaron sin referencias externas.
  - Pipeline: lint y typecheck limpios, 121 de 121 pruebas aprobadas y build PWA exitoso; precache de 50 entradas / 2,423.75 KiB.

### PERF-003 — Aplicar carga diferida de medios no críticos

- Prioridad: `P2`
- Estado: `COMPLETA`
- Dependencias: `PERF-001`
- Criterios de aceptación:
  - Imágenes fuera del viewport usan carga diferida cuando corresponde.
  - Se reservan dimensiones para evitar saltos de layout.
  - La imagen LCP se prioriza sin precargar recursos innecesarios.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Archivos modificados:
  - `pwa/src/features/auth/pages/AuthPage.tsx`
  - `pwa/src/features/onboarding/pages/OnboardingPage.tsx`
  - `pwa/src/features/onboarding/components/PlayerCardBack.tsx`
  - `pwa/src/features/game/components/modals/GameIntroModal.tsx`
  - `pwa/src/features/game/pages/StadiumPage.tsx`
  - `pwa/mediaLoading.test.ts`
- Evidencia:
  - Login, introducción del partido y apertura del sobre emiten preload AVIF únicamente cuando su pantalla o paso está montado; móvil y escritorio usan condiciones `media` mutuamente excluyentes.
  - El logo crítico de autenticación usa prioridad alta y dimensiones intrínsecas 256×256.
  - El logo repetido en el reverso de las cartas usa `loading="lazy"`, decodificación asíncrona y dimensiones 128×128.
  - Logos de equipos y fotografías de pitchers reservan dimensiones 64×64 y 48×48 para evitar saltos de layout.
  - El audio `playball-stadium.mp3` solo se monta y precarga cuando el modal de introducción está realmente visible.
  - Tres pruebas de política verifican preloads por pantalla, dimensiones/carga diferida y montaje condicional del audio.
  - Pipeline: lint y typecheck limpios, 124 de 124 pruebas aprobadas y build PWA exitoso; precache de 50 entradas / 2,424.68 KiB.

### PERF-004 — Cumplir presupuesto y objetivos Lighthouse

- Prioridad: `P1`
- Estado: `EN CURSO`
- Dependencias: `PERF-001`, `PERF-002`, `PERF-003`, `SW-002`
- Criterios de aceptación:
  - El bundle JavaScript inicial se mantiene por debajo del límite de 250 KB gzip.
  - Se ejecuta Lighthouse móvil y escritorio sobre build de producción.
  - Performance, PWA, Accessibility y Best Practices alcanzan el objetivo definido en `pwa_analysis.md`.
  - El reporte queda guardado como evidencia o enlazado desde esta tarea.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Evidencia inicial:
  - El bundle inicial actual es 115.48 KiB gzip, por debajo del límite de 250 KB; Vite todavía advierte que el chunk minificado sin gzip supera 350 KB.
  - Lighthouse 13.4.1 ejecutado sobre `/auth` en build de producción; los reportes JSON/HTML y la comparación se guardaron en `pwa/reports/lighthouse/`.
  - Línea base móvil: Performance 65, Accessibility 100, Best Practices 100, FCP 3.6 s, LCP 5.8 s y CLS 0.
  - Medición optimizada móvil: Performance 83, Accessibility 100, Best Practices 100, FCP 2.4 s, LCP 4.0 s y CLS 0.016.
  - Medición optimizada escritorio: Performance 98, Accessibility 100, Best Practices 100, FCP 0.7 s, LCP 1.0 s y CLS 0.003.
  - El logo principal pasó de PNG 256×256 de 124 KiB a AVIF 128×128 de 6.4 KiB con respaldo PNG; la pantalla de autenticación evita un salto de chunk y el runtime de sincronización/actualización se difiere hasta tiempo ocioso.
  - El bundle inicial optimizado es 114.53 KiB gzip y el pipeline permanece limpio con 124 de 124 pruebas aprobadas.
  - Lighthouse 13 ya no publica categoría PWA; manifest, service worker e instalación se cubren con evidencia automatizada y la validación manual de `PWA-004`.
  - Pendiente para cierre: elevar Performance móvil de 83 a la zona verde, principalmente reduciendo CSS global bloqueante y JavaScript no utilizado en la ruta de acceso.
  - Experimentos descartados con evidencia: fuentes locales WOFF2 redujeron Performance a 80 y retirar el preload contextual del fondo a 76; se restauró la variante estable de 83.
  - Separar el aviso de instalación en otro chunk redujo apenas 0.7 KiB gzip del bundle inicial y bajó Performance móvil a 73 por la solicitud compartida adicional; también se revirtió.

---

## Fase 5 — Accesibilidad y movimiento

### A11Y-001 — Corregir semántica y foco de diálogos

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - Los modales de juego tienen `role=dialog`, `aria-modal` y nombre accesible.
  - El foco entra al diálogo, queda contenido y vuelve al disparador al cerrar.
  - Escape cierra únicamente cuando hacerlo es seguro.
  - Los botones de icono tienen nombre accesible.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Evidencia:
  - Se añadió `useDialogFocus`, una utilidad compartida que mueve el foco al abrir, contiene Tab/Shift+Tab y devuelve el foco al elemento disparador.
  - Escape se habilita únicamente en diálogos cancelables y se desactiva durante operaciones de carga.
  - `Modal`, `ChangePitcherModal`, `QuitGameModal`, `GameOverModal`, `InningTransitionModal`, `GameIntroModal`, `RivalPitcherChangeModal` y el selector de lanzamiento exponen rol, modalidad, nombre accesible y foco programático.
  - Los botones de cierre mediante icono tienen nombre accesible; los errores de selección se exponen como alertas.
  - `PlayResultOverlay` se clasificó como estado dinámico no interactivo y queda dentro del alcance de `A11Y-003`, no como diálogo.
  - Una prueba de interacción verifica foco inicial, ciclo de Tab, cierre con Escape y retorno al disparador; siete casos estructurales protegen la semántica de todos los diálogos de juego.
  - Pipeline: lint y typecheck limpios, 132 de 132 pruebas aprobadas y build PWA exitoso; precache de 49 entradas / 2,435.46 KiB.

### A11Y-002 — Validar navegación completa por teclado

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `A11Y-001`
- Criterios de aceptación:
  - Todas las acciones principales funcionan sin ratón.
  - El orden del foco sigue el orden visual y no queda atrapado fuera de modales.
  - El foco visible cumple contraste y no se oculta.
  - Carruseles y selecciones exponen estado seleccionado.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Evidencia:
  - Las pestañas de autenticación implementan patrón roving tabindex y navegación con flechas, Home y End.
  - El carrusel compartido de franquicias/rivales implementa listbox con opciones seleccionadas, roving tabindex, flechas, Home/End, foco y desplazamiento del elemento activo.
  - Las cartas tácticas usan botones nativos con `aria-pressed`, `disabled` real y foco visible.
  - Cartas seleccionables, posiciones del lineup, pitcher titular, zonas y tipos de lanzamiento exponen su estado seleccionado y foco visible.
  - Los controles bloqueados del selector de pitcheo y la zona usan `disabled`; ya no dependen solamente de `pointer-events-none`.
  - La carta interactiva del pitcher responde a Enter y Espacio, tiene nombre accesible y solo muestra cursor de acción cuando permite el cambio.
  - Dos pruebas validan navegación del carrusel y la política de selección/foco/deshabilitado; se auditó el uso de `onClick` para descartar controles principales inaccesibles.
  - Pipeline: lint y typecheck limpios, 134 de 134 pruebas aprobadas y build PWA exitoso; precache de 49 entradas / 2,437.14 KiB.

### A11Y-003 — Añadir anuncios de estado dinámico

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: `OFF-005`
- Criterios de aceptación:
  - Resultados, errores, conexión y actualizaciones críticas usan `aria-live` apropiado.
  - No se anuncian cambios decorativos o repetitivos.
  - Los mensajes conservan significado sin depender del color.
- Responsable: Codex
- Fecha de inicio: 2026-09-05
- Evidencia:
  - `PlayResultOverlay` mantiene una región `status` persistente, `polite` y atómica que anuncia una sola vez el tipo de jugada y su descripción.
  - Toda la presentación animada del resultado se oculta al árbol accesible para evitar anuncios duplicados de emoji, título y texto.
  - Desconexión, fallos de sincronización, errores de gameplay, roster, formularios y guardado usan `alert`/`assertive`.
  - Sincronización, reconexión, actualizaciones PWA, confirmaciones y progreso de guardado usan `status`/`polite`.
  - Los mensajes contienen texto explícito y no dependen únicamente del color para comunicar su significado.
  - Dos pruebas nuevas validan prioridad de Toast y la política estructural de resultados, conexión, roster y guardado; la prueba de conectividad distingue desconexión urgente de recuperación informativa.
  - Pipeline: lint y typecheck limpios, 136 de 136 pruebas aprobadas y build PWA exitoso; precache de 49 entradas / 2,437.51 KiB.

### A11Y-004 — Definir título y contexto por ruta

- Prioridad: `P2`
- Estado: `COMPLETA`
- Dependencias: ninguna
- Criterios de aceptación:
  - Cada pantalla principal actualiza `document.title`.
  - El idioma del documento coincide con el idioma activo.
  - Los encabezados mantienen una jerarquía lógica.
- Responsable: Codex
- Fecha de inicio: 2026-09-05
- Evidencia:
  - `useRouteMetadata` centraliza el título de acceso, onboarding, lobby, equipo, colección, roster y gameplay, incluidas las rutas dinámicas `/roster/:id` y `/game/:id`.
  - Las rutas conocidas usan un título localizado seguido del nombre del producto; las rutas desconocidas conservan `Deck at the Plate` como título seguro.
  - El atributo `lang` del documento se sincroniza con el idioma resuelto por i18next y se actualiza al cambiar entre español e inglés.
  - Lobby ahora expone un único `h1` para su contenido principal y una jerarquía `h1`/`h2`; Mi Equipo ya no salta directamente de `h1` a `h3`.
  - Dos pruebas cubren rutas dinámicas, título localizado y cambio de idioma.
  - Pipeline: lint y typecheck limpios, 138 de 138 pruebas aprobadas y build PWA exitoso; precache de 49 entradas / 2,438.37 KiB.

### A11Y-005 — Validar contraste, zoom y lectores de pantalla

- Prioridad: `P1`
- Estado: `EN CURSO`
- Dependencias: `A11Y-001`, `A11Y-002`, `A11Y-003`, `A11Y-004`
- Criterios de aceptación:
  - Texto y controles cumplen WCAG AA.
  - La interfaz sigue operable con zoom de 200% y texto ampliado.
  - Se realiza una pasada con VoiceOver o lector equivalente.
  - Los problemas encontrados quedan corregidos o documentados con decisión explícita.
- Responsable: Codex
- Fecha de inicio: 2026-09-05
- Evidencia parcial:
  - Lighthouse 13.4.1 mantiene Accessibility 100 en móvil y escritorio para la pantalla de acceso, incluidos los chequeos automatizados de contraste.
  - La inspección del árbol accesible confirma encabezado, selector de idioma, pestañas, campos, control de visibilidad de contraseña y acción principal con nombre y rol reconocibles.
  - La pantalla de acceso se revisó renderizada sin pérdida visual ni controles inaccesibles; el pipeline permanece limpio con 139 de 139 pruebas.
  - Pendiente para cierre: pasada manual del flujo completo con zoom real al 200%, texto ampliado y VoiceOver en macOS. Esta comprobación no se sustituye por Lighthouse ni por pruebas DOM.

### MOT-001 — Respetar reducción de movimiento en JavaScript

- Prioridad: `P1`
- Estado: `COMPLETA`
- Dependencias: ninguna
- Criterios de aceptación:
  - Animaciones de Framer Motion consultan `useReducedMotion` o equivalente.
  - Efectos de rareza, partículas y transiciones tienen alternativa reducida.
  - La preferencia CSS y JavaScript produce una experiencia coherente.
- Responsable: Codex
- Fecha de inicio: 2026-09-05
- Evidencia:
  - El proveedor raíz configura `MotionConfig reducedMotion="user"`, por lo que todas las animaciones Framer Motion respetan automáticamente la preferencia del sistema.
  - En modo reducido Framer Motion elimina transformaciones y animaciones de layout, incluidas entradas, escalas, desplazamientos, rotaciones y efectos repetidos, manteniendo cambios no espaciales necesarios para comunicar estado.
  - La política global se combina con el bloque CSS existente `prefers-reduced-motion: reduce`, que neutraliza keyframes y transiciones CSS, incluidas partículas y animaciones del sobre.
  - Una prueba nueva simula la preferencia del sistema y verifica que `useReducedMotion` recibe `true` dentro del proveedor.
  - Pipeline: lint y typecheck limpios, 139 de 139 pruebas aprobadas y build PWA exitoso; precache de 49 entradas / 2,438.56 KiB.

---

## Fase 6 — Arquitectura, estado y estilos

### ARCH-001 — Dividir StadiumPage por responsabilidades

- Prioridad: `P2`
- Estado: `EN CURSO`
- Dependencias: `QLT-005`
- Hallazgo inicial: `StadiumPage.tsx` tiene aproximadamente 1491 líneas.
- Criterios de aceptación:
  - Estado/orquestación, marcador, jugadores, acciones, bases y overlays están separados coherentemente.
  - La extracción no duplica lógica ni cambia comportamiento.
  - Los componentes resultantes tienen pruebas enfocadas.
- Responsable: Codex
- Fecha de inicio: 2026-09-05
- Evidencia parcial:
  - Se extrajeron encabezado, marcador, conteo, inning y diamante de bases a `components/stadium/GameStatusPanels.tsx`; `StadiumPage` conserva únicamente su composición y datos.
  - También se separaron la carga visual de stamina/lanzamientos y el resumen del siguiente bateador en `PlayerMetaPanels.tsx`, conservando modelos de entrada mínimos y sin acoplarlos al store.
  - La cuadrícula duplicada de estadísticas de pitcher/bateador se consolidó en `PlayerStats.tsx`; conserva hover, animación, estilos de rareza circundantes y notifica la selección mediante callback.
  - Los armazones completos de pitcher y bateador se movieron a `PlayerCards.tsx`; un `CardShell` privado comparte identidad, rareza y estadísticas, mientras las exportaciones preservan las props originales.
  - Los modelos `PitcherSummary` y `BatterSummary` viven en `playerPanelTypes.ts`, evitando dependencias circulares entre transformación de datos y presentación.
  - La mano táctica y el botón de acción se movieron a `GameActionControls.tsx`, conservando selección accesible, estados deshabilitados, animaciones y callbacks explícitos.
  - La cuadrícula interactiva se movió a `StrikeZone.tsx`; sus nueve botones conservan nombre accesible, `aria-pressed`, bloqueo real mediante `disabled` y visualización del lanzamiento seleccionado.
  - `StadiumPage.tsx` bajó de aproximadamente 1491 a 898 líneas sin duplicar lógica ni cambiar las propiedades públicas de los componentes.
  - El SVG decorativo de bases se excluye explícitamente del árbol accesible y la etiqueta de rol conserva la política responsiva del módulo CSS.
  - Diez pruebas enfocadas verifican los paneles extraídos, incluida selección de zona, bloqueo de juego, selección táctica, acción principal y cambio de pitcher.
  - Pipeline: lint y typecheck limpios, 149 de 149 pruebas aprobadas y build PWA exitoso; precache de 49 entradas / 2,437.15 KiB.
  - Pendiente para cierre: extraer la lógica de transformación/carga y orquestación en unidades coherentes.

### ARCH-002 — Dividir pantallas y modales grandes restantes

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `QLT-005`
- Alcance inicial: Onboarding, RivalPitcherChangeModal, Lobby, MyTeam, PlayResultOverlay y RosterSelection.
- Criterios de aceptación:
  - Cada unidad tiene una responsabilidad reconocible.
  - La lógica compartida se mueve a hooks/utilidades sin sobreabstracción.
  - Se preservan rutas, accesibilidad y diseño responsivo.
- Evidencia: pendiente.

### ARCH-003 — Afinar selectores Zustand

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: ninguna
- Criterios de aceptación:
  - Los componentes seleccionan primitivas o usan `useShallow` cuando corresponde.
  - No se desestructura el store completo si provoca renderizados innecesarios.
  - Se verifica que las acciones mantengan referencias estables.
- Evidencia: pendiente.

### ARCH-004 — Centralizar estados de red en stores/servicios

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `OFF-004`
- Criterios de aceptación:
  - Carga, error y reintento no se implementan repetidamente en páginas.
  - Axios, polling y WebSocket comparten una política observable y consistente.
  - Las actualizaciones del lineup refrescan las estadísticas dependientes.
- Evidencia: pendiente.

### STYLE-001 — Consolidar tokens visuales

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: ninguna
- Criterios de aceptación:
  - Colores, espacios, radios, sombras y capas repetidos usan tokens.
  - Se reducen valores hexadecimales e inline styles duplicados.
  - Los tokens respetan contraste y los estados de interacción.
- Evidencia: pendiente.

### STYLE-002 — Resolver la política Tailwind/CSS Modules

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `STYLE-001`
- Decisión requerida: aplicar literalmente “solo Tailwind” o documentar CSS Modules como excepción aceptada.
- Criterios de aceptación:
  - La decisión queda registrada en la especificación o ADR.
  - El código nuevo sigue una convención única y verificable.
  - Los archivos CSS extensos se reducen o se justifican con límites claros.
- Evidencia: pendiente.

### STYLE-003 — Implementar modo oscuro basado en clase/proveedor

- Prioridad: `P3`
- Estado: `PENDIENTE`
- Dependencias: `STYLE-001`, `STYLE-002`
- Criterios de aceptación:
  - Existe una fuente única para la preferencia visual.
  - La selección se persiste y respeta preferencia del sistema cuando procede.
  - El cambio de tema no produce parpadeo inicial visible.
- Evidencia: pendiente.

---

## Fase 7 — Cobertura de pruebas

### TEST-001 — Ampliar pruebas de stores y API

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `QLT-005`, `ARCH-004`
- Criterios de aceptación:
  - Stores críticos prueban éxito, error, carga, reintento y reset.
  - Interceptores JWT y renovación/rechazo se prueban sin red real.
  - Los tests son deterministas y aíslan persistencia.
- Evidencia: pendiente.

### TEST-002 — Probar WebSocket, polling y recuperación

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `ARCH-004`
- Criterios de aceptación:
  - Se prueban reconexión con backoff, mensajes duplicados y caída de socket.
  - El fallback de polling se activa y cancela correctamente.
  - No quedan temporizadores o conexiones abiertas al terminar las pruebas.
- Evidencia: pendiente.

### TEST-003 — Probar persistencia, offline y sincronización

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `OFF-001`, `OFF-002`, `OFF-003`, `OFF-004`
- Criterios de aceptación:
  - Se prueban migraciones IndexedDB, cola, reintentos, duplicados y conflictos.
  - Se simula perder y recuperar conectividad.
  - El estado final coincide con la autoridad del backend.
- Evidencia: pendiente.

### TEST-004 — Añadir flujos E2E críticos

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `TEST-001`, `TEST-002`, `TEST-003`
- Criterios de aceptación:
  - Playwright o equivalente cubre autenticación, onboarding, lobby, roster y gameplay principal.
  - Hay al menos un flujo offline/reconexión.
  - Los fallos producen trazas/capturas útiles.
- Evidencia: pendiente.

### TEST-005 — Matriz manual de navegadores y dispositivos

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `TEST-004`, `PWA-004`
- Criterios de aceptación:
  - Se validan Chrome, Edge y Safari en los sistemas definidos por el proyecto.
  - Se cubren móvil, escritorio, standalone y recarga profunda.
  - Los resultados y excepciones quedan documentados.
- Evidencia: pendiente.

---

## Fase 8 — Repositorio, validación final y documentación

### REPO-001 — Limpiar artefactos temporales del árbol fuente

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `QLT-001`
- Alcance detectado: backups de Stadium, pruebas experimentales sin integrar y `.DS_Store` en recursos públicos.
- Criterios de aceptación:
  - No hay archivos `.backup`, `.bak*`, `.DS_Store` ni artefactos temporales dentro de producción.
  - Antes de eliminar, se confirma que ningún archivo contiene trabajo único necesario.
  - El árbol fuente solo incluye pruebas configuradas y mantenidas.
- Evidencia: pendiente.

### REPO-002 — Fortalecer `.gitignore`

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: ninguna
- Criterios de aceptación:
  - Se ignoran `.env.*` excepto ejemplos aprobados.
  - Se ignoran backups, archivos del sistema y reportes locales generados.
  - No se ignoran archivos necesarios para reproducir build o pruebas.
- Evidencia: pendiente.

### CI-001 — Añadir puertas de calidad en integración continua

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - CI ejecuta instalación reproducible, lint, typecheck, test y build.
  - Una falla impide integrar cambios.
  - Los resultados quedan visibles por commit/PR.
- Evidencia: pendiente.

### DOC-001 — Actualizar checklist de `pwa_analysis.md`

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: todas las tareas funcionales correspondientes
- Criterios de aceptación:
  - La lista refleja lo realmente implementado y validado.
  - No se marca una regla solo por existir código parcial.
  - Las excepciones acordadas incluyen justificación y fecha.
- Evidencia: pendiente.

### REL-001 — Auditoría final de cumplimiento

- Prioridad: `P0`
- Estado: `PENDIENTE`
- Dependencias: todas las fases anteriores
- Criterios de aceptación:
  - `lint`, `typecheck`, `test` y `build` están verdes en limpio y en CI.
  - Lighthouse y la validación manual cumplen los objetivos acordados.
  - Instalación, actualización, offline y recuperación se validan en dispositivos objetivo.
  - Cada regla de `pwa_analysis.md` tiene evidencia o una excepción aprobada.
  - El resumen de este documento muestra 45 de 45 tareas completas.
- Evidencia: pendiente.

---

## Orden de ejecución recomendado

1. `QLT-001` a `QLT-005`: recuperar una base compilable y confiable.
2. `PWA-001` a `PWA-003` y `PERF-001`: completar metadatos y reducir activos antes de ajustar el precache.
3. `OFF-001` a `OFF-005`: construir persistencia, cola y experiencia offline.
4. `SW-001` a `SW-004`: formalizar cache, actualización e instalación.
5. `A11Y-001` a `MOT-001`: completar accesibilidad y reducción de movimiento.
6. `ARCH-001` a `STYLE-003`: reducir deuda estructural sin bloquear los requisitos esenciales.
7. `TEST-001` a `TEST-005`: cerrar cobertura automatizada y matriz manual.
8. `PERF-004`, `REPO-001`, `REPO-002`, `CI-001`, `DOC-001` y `REL-001`: medición, higiene y cierre.

## Plantilla de actualización de una tarea

Copiar este bloque dentro de la tarea al iniciarla:

```md
- Responsable: nombre o tarea de Codex
- Fecha de inicio: AAAA-MM-DD
- Archivos previstos:
  - `ruta/al/archivo`
- Decisiones:
  - decisión y motivo
- Evidencia:
  - `npm run ...`: resultado
  - Captura/reporte: ruta o enlace
  - Commit: `hash mensaje`
```

## Registro de decisiones

| ID | Fecha | Decisión | Motivo | Impacto |
| --- | --- | --- | --- | --- |
| DEC-001 | 2026-09-04 | Mantener `pwa_analysis.md` como especificación y este archivo como tablero. | Evita mezclar reglas normativas con progreso operativo. | Toda tarea se vincula a criterios verificables sin reescribir la especificación. |

## Registro de revisiones

| Fecha | Cambio | Autor |
| --- | --- | --- |
| 2026-09-04 | Creación del plan a partir de la auditoría inicial del frontend PWA. | Codex |
| 2026-09-04 | PERF-004 medido y optimizado parcialmente: móvil 65→83 y escritorio 98; permanece en curso hasta alcanzar Performance móvil verde. | Codex |
