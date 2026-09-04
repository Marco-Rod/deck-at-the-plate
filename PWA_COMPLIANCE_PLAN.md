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
| 0. Estabilización | 5 | 3 | EN CURSO |
| 1. Instalación PWA | 4 | 0 | PENDIENTE |
| 2. Persistencia y offline | 5 | 0 | PENDIENTE |
| 3. Service worker | 4 | 0 | PENDIENTE |
| 4. Rendimiento | 4 | 0 | PENDIENTE |
| 5. Accesibilidad y movimiento | 6 | 0 | PENDIENTE |
| 6. Arquitectura y estilos | 7 | 0 | PENDIENTE |
| 7. Cobertura de pruebas | 5 | 0 | PENDIENTE |
| 8. Validación y documentación | 5 | 0 | PENDIENTE |
| **Total** | **45** | **3** | **EN CURSO** |

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
- Estado: `EN CURSO`
- Dependencias: ninguna
- Alcance: `PlayResultOverlay`, `FloatingParticles`, `StadiumPage` y pruebas relacionadas, incluidas las expectativas CSS obsoletas detectadas en `QLT-001`.
- Criterios de aceptación:
  - No se ejecuta un `setState` síncrono innecesario dentro de efectos.
  - No se utiliza `Math.random()` durante renderizado.
  - No se lee o modifica una referencia de React durante renderizado de forma insegura.
  - No quedan advertencias de variables sin uso dentro del alcance.
- Responsable: Codex
- Fecha de inicio: 2026-09-04
- Evidencia: pendiente.

### QLT-005 — Recuperar pipeline local verde

- Prioridad: `P0`
- Estado: `PENDIENTE`
- Dependencias: `QLT-001`, `QLT-002`, `QLT-003`, `QLT-004`
- Criterios de aceptación:
  - `npm run lint` termina sin errores ni advertencias relevantes.
  - `npm run typecheck` termina con código 0.
  - `npm run test` termina con todas las pruebas aprobadas.
  - `npm run build` genera el artefacto de producción.
- Evidencia: pendiente.

---

## Fase 1 — Instalación PWA y metadatos

### PWA-001 — Completar el manifest

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - `short_name` tiene un máximo de 12 caracteres.
  - Se define la orientación requerida por la especificación.
  - Se conservan `start_url`, `display: standalone`, `theme_color` y `background_color` correctos.
  - El manifest generado pasa la validación de DevTools/Lighthouse.
- Evidencia: pendiente.

### PWA-002 — Generar iconos completos y maskable

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: ninguna
- Criterios de aceptación:
  - Existen iconos PNG válidos de 192×192 y 512×512.
  - Existe al menos un icono 512×512 con propósito `maskable` y zona segura verificada.
  - Existe `apple-touch-icon` de 180×180.
  - No se reutilizan imágenes que pierdan legibilidad al recortarse.
- Evidencia: pendiente.

### PWA-003 — Completar metadatos para iOS y viewport

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `PWA-002`
- Criterios de aceptación:
  - `index.html` enlaza el `apple-touch-icon`.
  - Incluye metadatos Apple necesarios para ejecución standalone.
  - Mantiene `viewport-fit=cover` y usa safe-area cuando corresponde.
- Evidencia: pendiente.

### PWA-004 — Validar instalación en navegadores objetivo

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `PWA-001`, `PWA-002`, `PWA-003`, `SW-003`
- Criterios de aceptación:
  - La aplicación es instalable en Chrome/Edge de escritorio y Android.
  - Se valida el comportamiento Add to Home Screen en Safari iOS.
  - Inicio desde icono abre la ruta y presentación esperadas.
- Evidencia: pendiente.

---

## Fase 2 — Persistencia y funcionamiento offline

### OFF-001 — Definir e implementar esquema IndexedDB con Dexie

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - Existe un módulo dedicado en `src/offline/`.
  - El esquema tiene versión explícita y stores para los datos persistentes requeridos.
  - Las credenciales sensibles no se almacenan en IndexedDB.
  - Hay pruebas unitarias del esquema y operaciones básicas.
- Evidencia: pendiente.

### OFF-002 — Migrar el estado de juego persistente desde localStorage

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `OFF-001`
- Criterios de aceptación:
  - El estado de juego que requiere persistencia usa IndexedDB.
  - La migración conserva datos existentes válidos o documenta su descarte seguro.
  - `localStorage` queda limitado a preferencias pequeñas y no sensibles.
  - Se prueban actualización de versión y migración.
- Evidencia: pendiente.

### OFF-003 — Implementar cola de mutaciones offline

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `OFF-001`
- Criterios de aceptación:
  - Las mutaciones soportadas se guardan con ID, payload, fecha, reintentos y estado.
  - La cola se drena al recuperar conexión sin duplicar operaciones.
  - Hay backoff y límite de reintentos.
  - Los errores permanentes son visibles y recuperables por el usuario.
- Evidencia: pendiente.

### OFF-004 — Definir conflicto y resincronización

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `OFF-003`
- Criterios de aceptación:
  - La estrategia de autoridad servidor/cliente está documentada por operación.
  - Los conflictos no sobrescriben silenciosamente datos más recientes.
  - Tras reconexión se refresca el estado autoritativo relevante.
  - Hay pruebas para duplicados, orden y conflicto.
- Evidencia: pendiente.

### OFF-005 — Añadir estado de conectividad en la interfaz

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `OFF-003`, `OFF-004`
- Criterios de aceptación:
  - La interfaz anuncia modo offline, reconexión y sincronización pendiente.
  - Los controles no disponibles explican el motivo.
  - Los cambios de estado se anuncian mediante una región accesible.
  - La experiencia no depende exclusivamente del color.
- Evidencia: pendiente.

---

## Fase 3 — Service worker y ciclo de actualización

### SW-001 — Configurar estrategias de runtime caching

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - APIs de lectura usan una estrategia compatible con frescura y tolerancia offline.
  - Recursos estáticos usan estrategias, expiración y límites definidos.
  - Respuestas privadas o mutaciones no se cachean de forma insegura.
  - Las reglas quedan documentadas y probadas.
- Evidencia: pendiente.

### SW-002 — Definir precache y fallback offline

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `PERF-001`
- Criterios de aceptación:
  - El precache excluye recursos innecesarios o excesivamente pesados.
  - Existe un fallback de navegación coherente.
  - Los recursos esenciales de la experiencia inicial están disponibles offline.
  - El tamaño final del precache queda registrado.
- Evidencia: pendiente.

### SW-003 — Implementar notificación y aplicación de actualizaciones

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `SW-001`, `SW-002`
- Criterios de aceptación:
  - La interfaz informa cuando existe una nueva versión.
  - El usuario puede actualizar de forma controlada sin perder una operación activa.
  - Se contempla revalidación al volver a una pestaña visible.
  - El flujo de actualización está probado.
- Evidencia: pendiente.

### SW-004 — Añadir experiencia de instalación

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `PWA-001`, `PWA-002`, `PWA-003`
- Criterios de aceptación:
  - Se maneja `beforeinstallprompt` cuando está disponible.
  - La sugerencia no interrumpe tareas críticas y puede descartarse.
  - En iOS se muestran instrucciones específicas solo cuando aplican.
  - Se evita mostrar la invitación si la app ya está instalada.
- Evidencia: pendiente.

---

## Fase 4 — Rendimiento

### PERF-001 — Optimizar imágenes y fondos pesados

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: ninguna
- Hallazgo inicial: hay PNG aproximados entre 1.4 MB y 2.5 MB y un precache superior a 13 MB.
- Criterios de aceptación:
  - Imágenes grandes se convierten a WebP/AVIF cuando sea compatible.
  - Existen tamaños responsivos para fondos y contenido relevante.
  - No se reduce perceptiblemente la calidad visual necesaria.
  - Se documentan pesos antes/después y ahorro total.
- Evidencia: pendiente.

### PERF-002 — Revisar carga y cache de tipografías

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `SW-001`
- Criterios de aceptación:
  - Las tipografías críticas no bloquean indefinidamente el contenido.
  - Se define `font-display` apropiado.
  - Cache y origen de fuentes quedan explícitos.
  - Se evita descargar variantes no utilizadas.
- Evidencia: pendiente.

### PERF-003 — Aplicar carga diferida de medios no críticos

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `PERF-001`
- Criterios de aceptación:
  - Imágenes fuera del viewport usan carga diferida cuando corresponde.
  - Se reservan dimensiones para evitar saltos de layout.
  - La imagen LCP se prioriza sin precargar recursos innecesarios.
- Evidencia: pendiente.

### PERF-004 — Cumplir presupuesto y objetivos Lighthouse

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `PERF-001`, `PERF-002`, `PERF-003`, `SW-002`
- Criterios de aceptación:
  - El bundle JavaScript inicial se mantiene por debajo del límite de 250 KB gzip.
  - Se ejecuta Lighthouse móvil y escritorio sobre build de producción.
  - Performance, PWA, Accessibility y Best Practices alcanzan el objetivo definido en `pwa_analysis.md`.
  - El reporte queda guardado como evidencia o enlazado desde esta tarea.
- Evidencia: pendiente.

---

## Fase 5 — Accesibilidad y movimiento

### A11Y-001 — Corregir semántica y foco de diálogos

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `QLT-005`
- Criterios de aceptación:
  - Los modales de juego tienen `role=dialog`, `aria-modal` y nombre accesible.
  - El foco entra al diálogo, queda contenido y vuelve al disparador al cerrar.
  - Escape cierra únicamente cuando hacerlo es seguro.
  - Los botones de icono tienen nombre accesible.
- Evidencia: pendiente.

### A11Y-002 — Validar navegación completa por teclado

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `A11Y-001`
- Criterios de aceptación:
  - Todas las acciones principales funcionan sin ratón.
  - El orden del foco sigue el orden visual y no queda atrapado fuera de modales.
  - El foco visible cumple contraste y no se oculta.
  - Carruseles y selecciones exponen estado seleccionado.
- Evidencia: pendiente.

### A11Y-003 — Añadir anuncios de estado dinámico

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `OFF-005`
- Criterios de aceptación:
  - Resultados, errores, conexión y actualizaciones críticas usan `aria-live` apropiado.
  - No se anuncian cambios decorativos o repetitivos.
  - Los mensajes conservan significado sin depender del color.
- Evidencia: pendiente.

### A11Y-004 — Definir título y contexto por ruta

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: ninguna
- Criterios de aceptación:
  - Cada pantalla principal actualiza `document.title`.
  - El idioma del documento coincide con el idioma activo.
  - Los encabezados mantienen una jerarquía lógica.
- Evidencia: pendiente.

### A11Y-005 — Validar contraste, zoom y lectores de pantalla

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: `A11Y-001`, `A11Y-002`, `A11Y-003`, `A11Y-004`
- Criterios de aceptación:
  - Texto y controles cumplen WCAG AA.
  - La interfaz sigue operable con zoom de 200% y texto ampliado.
  - Se realiza una pasada con VoiceOver o lector equivalente.
  - Los problemas encontrados quedan corregidos o documentados con decisión explícita.
- Evidencia: pendiente.

### MOT-001 — Respetar reducción de movimiento en JavaScript

- Prioridad: `P1`
- Estado: `PENDIENTE`
- Dependencias: ninguna
- Criterios de aceptación:
  - Animaciones de Framer Motion consultan `useReducedMotion` o equivalente.
  - Efectos de rareza, partículas y transiciones tienen alternativa reducida.
  - La preferencia CSS y JavaScript produce una experiencia coherente.
- Evidencia: pendiente.

---

## Fase 6 — Arquitectura, estado y estilos

### ARCH-001 — Dividir StadiumPage por responsabilidades

- Prioridad: `P2`
- Estado: `PENDIENTE`
- Dependencias: `QLT-005`
- Hallazgo inicial: `StadiumPage.tsx` tiene aproximadamente 1491 líneas.
- Criterios de aceptación:
  - Estado/orquestación, marcador, jugadores, acciones, bases y overlays están separados coherentemente.
  - La extracción no duplica lógica ni cambia comportamiento.
  - Los componentes resultantes tienen pruebas enfocadas.
- Evidencia: pendiente.

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
