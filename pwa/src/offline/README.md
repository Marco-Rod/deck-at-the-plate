# Política de datos offline

El servidor conserva la autoridad final sobre los datos compartidos. IndexedDB permite continuidad local, pero no convierte al cliente en la fuente de verdad.

## Operaciones

| Operación | Comportamiento offline | Conflicto y resincronización |
| --- | --- | --- |
| `lineup.save` | Se conserva únicamente el último lineup deseado por usuario. La primera edición guarda como línea base el último lineup confirmado por el servidor. | Antes del `PUT` se consulta el lineup remoto. Si coincide con el deseado, la operación se considera aplicada. Si coincide con la línea base, se envía el cambio. Si difiere de ambos, se detiene y se muestra el conflicto sin sobrescribir el servidor. Después se refresca el lineup remoto. |
| Estado de juego | Se persiste una copia de recuperación, pero no se envían mutaciones diferidas. | Al reconectar, WebSocket/API vuelve a ser la autoridad. Los datos transitorios del lanzamiento no se persisten. |
| `pitch`, `swing`, `steal`, `play-tactic`, cambio de pitcher | No se admiten offline. | Son acciones ligadas al turno; deben repetirse explícitamente sobre el estado vigente. |
| Crear partida, crear club, reclamar sobre | No se admiten offline. | Pueden generar recursos o recompensas y requieren confirmación inmediata del servidor. |

## Orden, duplicados y errores

- Las operaciones se procesan por `createdAt` y de manera secuencial.
- `dedupeKey` reemplaza cambios pendientes equivalentes con el último estado deseado.
- Una respuesta ya aplicada es idempotente y evita repetir el `PUT`.
- Errores de red y respuestas 5xx usan backoff exponencial con límite de intentos.
- Rechazos 4xx y conflictos pasan directamente a `failed`.
- El usuario puede reintentar o descartar una operación fallida. Descartarla conserva el estado autoritativo recién obtenido del servidor.

## Cache Storage del service worker

| Recurso | Estrategia | Límite |
| --- | --- | --- |
| `GET /api/v1/teams/cpu` y `GET /api/v1/cards/:id` | Network First, timeout de 4 segundos | 60 respuestas durante 1 hora |
| CSS de `fonts.googleapis.com` | Stale While Revalidate | 6 respuestas durante 30 días |
| Imágenes solicitadas en runtime | Cache First | 80 respuestas durante 30 días |
| Fuentes de `fonts.gstatic.com` | Cache First | 12 respuestas durante 1 año |

Las rutas privadas (`profile`, inventario, lineup, equipo y partidas) no se guardan en Cache Storage. Tampoco existe ninguna regla runtime para `POST`, `PUT`, `PATCH` o `DELETE`; las únicas mutaciones diferidas admitidas utilizan la cola IndexedDB descrita arriba.

## Precache y navegación offline

El precache contiene el app shell (`index.html`), bundles con hash, manifest, iconos, favicon, logo compacto y fondos AVIF. Los PNG de alta resolución equivalentes quedan excluidos para no duplicar varios megabytes; continúan disponibles como fallback por red y el cache runtime de imágenes los conserva únicamente cuando un navegador los solicita.

Las navegaciones usan `/index.html` como fallback offline para que React Router pueda resolver rutas internas. Las rutas `/api/` están explícitamente excluidas de este fallback y nunca reciben HTML como si fuera una respuesta JSON.
