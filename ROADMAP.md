# Deck at the Plate — Roadmap del Proyecto

Última actualización: 2026-08-23

---

## Estado General

| Área | Estado |
|---|---|
| Infraestructura Docker | ✅ Funcional |
| Backend — Autenticación | ✅ Funcional |
| Backend — Motor del juego | ✅ Funcional (bugs críticos corregidos) |
| Backend — Economía / Tienda | ✅ Funcional |
| Frontend — Flujo de navegación | ✅ Funcional |
| Frontend — Pantalla de juego (estadio) | 🟡 Parcial — loop jugable, CPU no responde sola |
| Frontend — Mi Equipo | 🟡 Parcial — conectado a API, sin edición |
| Frontend — Tienda | 🔴 Sin pantalla |
| Modo PvP real | 🔴 No implementado |

---

## Core Loop del Juego

```
Registro / Login
      ↓
Starter Pack (tienda o auto al registrarse)
      ↓
Lobby → Selección de Roster → Partida (PvE o PvP)
      ↓
Ganar Stamps → Abrir Sobres → Mejorar inventario
      ↓
Repetir
```

---

## Lo que es usable hoy

### Infraestructura
- Docker Compose levanta los 3 servicios (DB, backend, frontend) sin intervención manual.
- La base de datos se inicializa automáticamente con `create_all` al arrancar el backend.
- Alembic configurado para migraciones versionadas (aún sin primera migración generada).
- Variables de entorno separadas del código fuente (`.env` / `.env.example`).

### Autenticación
- Registro de usuario con validación de username único y contraseña hasheada (bcrypt).
- Login con JWT Bearer token de 8 horas de vigencia.
- `AuthScreen` conectado a la API real: muestra errores del servidor, deshabilita el botón durante la petición.
- Sesión persistida en `localStorage` y restaurada al recargar.

### Catálogo y economía
- Listado de equipos y roster por equipo (`GET /api/v1/cards/teams`).
- Detalle de carta individual (`GET /api/v1/cards/{card_id}`).
- Starter pack: 10 cartas del equipo elegido asignadas al inventario (`POST /api/v1/shop/starter-pack`).
- Apertura de sobres con probabilidades ponderadas por rareza y descuento de stamps (`POST /api/v1/shop/open-pack`): tipos BRONZE (500 stamps / 3 cartas), GOLD (1500 / 4), DIAMOND (4000 / 5).
- Wallet del usuario con stamps y gems consultable via API.

### Mi Equipo (frontend)
- Carga el inventario real del usuario desde la API.
- Separa automáticamente pitchers (`SP`, `RP`, `TWP`) de bateadores.
- Muestra atributos reales de cada carta: `overall`, `contact`, `power`, `velocity`, `control`, `movement`.
- Maneja estados de carga, error y lista vacía.

### Flujo de inicio de partida
- `LobbyScreen` permite elegir modo (PvE / PvP) y dificultad (Easy / Medium / Hard).
- `RosterSelectionScreen` carga el inventario real, permite elegir pitcher y hasta 9 bateadores.
- Al confirmar, llama a `POST /api/v1/games/create` y navega al estadio con el `game_id` real.
- El botón de confirmación está deshabilitado hasta completar el roster (9 bateadores + 1 pitcher).

### Pantalla de juego (estadio)
- Conexión WebSocket establecida correctamente a `/ws/games/{game_id}/{user_id}`.
- Indicador visual de estado de conexión (verde / rojo).
- Grid 3×3 de selección de zona (Z1–Z9).
- Selector de tipo de lanzamiento con etiquetas en español (RECTA, SLIDER, CURVA, CAMBIO, BASE INTENCIONAL).
- Dock de cartas tácticas en mano (datos demo, no conectados al mazo real aún).
- Botón LANZAR / BATEAR envía la acción al backend via REST.
- Marcador actualizable en tiempo real: inning, half, score, conteo (B/S/O).
- Overlay de resultado de jugada al recibir `PLAY_RESOLVED` por WebSocket.
- Aviso visual al bateador cuando el lanzador ya pichó (`PITCH_COMMITTED`).

### Motor del juego (backend — 100% funcional)
- Conteo acumulativo de bolas, strikes y fouls.
- Cierre de at-bat: strikeout (3 strikes), walk (4 bolas), hits, outs directos.
- Avance de corredores y anotación de carreras para todos los eventos: WALK, HIT_1B, HIT_2B, HIT_3B, HOME_RUN.
- **Triple habilitado** (umbral corregido en `calculator.py`).
- Fatiga del pitcher a partir de 60 lanzamientos (degradación progresiva hasta −50%).
- Rotación automática del orden al bat (lineup de 9, módulo 9).
- Cambio de media entrada al 3er out.
- Extra innings con ghost runner en segunda base a partir del inning 10.
- Fog of War: el bateador no puede ver la zona ni el tipo de picheo del rival.
- Tres condiciones de fin de juego: walk-off, victoria directa en la alta, cierre de baja con outs.
- Cartas tácticas: activación, descarte, robo de carta al cambiar de entrada.

---

## Pendiente — Próximas prioridades

### P0 — Bloqueante para partida PvE jugable sin intervención manual

**CPU que responde automáticamente (el más urgente)**
- `trigger_cpu_response_if_needed()` existe en `gameplay.py` pero nunca se llama.
- Debe invocarse al final de `select_pitch` (para que CPU batee) y al final de `execute_swing` (para que CPU pichee).
- Sin esto el usuario tiene que alternar el selector de rol manualmente para simular ambos turnos.

**Pantalla de fin de juego**
- Cuando `state_data.is_game_over = true` no se muestra ninguna pantalla de resultado.
- El juego se queda congelado en el estadio sin notificar al jugador quién ganó.

**Estado inicial al conectar al WS**
- El evento `INIT_GAME_STATE` se recibe pero no se procesa: la pantalla arranca en blanco hasta la primera jugada.
- Solución: al recibir `INIT_GAME_STATE`, cargar el estado vía `GET /api/v1/games/{id}` y poblar `gameState`.

### P1 — Completar el loop de juego

**Cartas tácticas en el estadio conectadas al mazo real**
- `TacticalHand` muestra 4 cartas hardcodeadas en lugar del mazo real del jugador.
- El backend ya gestiona el deck/hand/discard correctamente; falta conectar la respuesta del WS al componente.

**Pantalla de tienda (ShopScreen)**
- Los endpoints de compra de sobres y starter pack están completos en el backend.
- No existe ninguna página en el frontend para acceder a ellos.
- El usuario no tiene forma de conseguir cartas desde la UI.

**Álbum de cartas conectado a la API**
- `CardShowcaseScreen` sigue con datos hardcodeados.
- Debe conectarse a `GET /api/v1/cards/teams` y mostrar el inventario real.

**Robo de base desde la UI**
- Endpoint `POST /{game_id}/steal` completamente funcional en el backend.
- No hay botón ni interfaz en el estadio para ejecutarlo.

**Cambio de pitcher desde la UI**
- Endpoint `POST /{game_id}/change-pitcher` completamente funcional.
- No hay panel de bullpen ni UI para realizar la sustitución.

**Swing tipo BUNT**
- `resolve_bunt()` implementado en `tactical_actions.py` y manejado en `execute_swing`.
- No hay opción de BUNT en el selector de swing de la UI.

### P2 — Mejoras de experiencia

- Fotos reales de jugadores (actualmente URLs de ESPN que pueden expirar o no existir).
- Animación de apertura de sobres (pack opening) al comprar en la tienda.
- Pantalla de historial de partidas jugadas.
- Mejoras de accesibilidad en el estadio (`aria-live` en el overlay, roles semánticos).
- Soporte a pantallas móviles (el estadio no está optimizado para viewport < 768px).
- Sonido contextual en eventos de juego (home run, strikeout, etc.) usando `audioManager.js`.

### P3 — Modo PvP real

- Sistema de matchmaking o sala de espera para conectar dos jugadores.
- El turn guard ya valida por `user_id`, el WebSocket ya soporta múltiples conexiones por partida.
- Falta la lógica de lobby PvP: invitación, handshake de inicio y sincronización de roles.

---

## Backlog futuro

- **Modo Torneo Koshien**: eliminatoria PvE con fatiga acumulativa entre partidas.
- **Eventos Semanales**: partidas con reglas especiales (estadio específico, condición climática).
- **Liga Ranked**: clasificación temporal con sistema de puntos ELO.
- **Mercado de Intercambio**: subastas y trades de cartas entre usuarios.
- **Cartas de Momentos Históricos**: ediciones especiales de jugadores con stats de temporadas específicas.
- **Estadísticas post-partida**: desglose de BA, OBP, whiff%, pitches por inning.

---

## Arquitectura de datos (referencia)

| Tabla | Descripción |
|---|---|
| `teams` | Equipos MLB (id, name, city, colores) |
| `player_cards` | Cartas globales de jugadores con atributos individuales |
| `tactic_cards` | Cartas tácticas con efectos JSON |
| `users` | Usuarios registrados |
| `user_wallets` | Stamps y Gems por usuario |
| `user_card_inventories` | Cartas en posesión de cada usuario |
| `game_sessions` | Sesiones de juego con state_data JSONB |

### Sistema de rareza

| Rarity | OVR | Stamps para abrirlo |
|---|---|---|
| COMMON | 58–65 | Solo en starter pack |
| BRONZE | 66–73 | Sobre BRONZE (500) |
| SILVER | 74–81 | Sobre BRONZE/GOLD |
| GOLD | 82–89 | Sobre GOLD (1500) |
| DIAMOND | 90–99 | Sobre DIAMOND (4000) |

---

## Comandos útiles

```bash
# Levantar el proyecto completo
docker compose up

# Ejecutar el seed con datos MLB 2025
docker compose exec backend python -m app.seeds.seed_real_data_2025

# Generar primera migración Alembic
docker compose exec backend alembic revision --autogenerate -m "baseline_schema"

# Aplicar migraciones pendientes
docker compose exec backend alembic upgrade head

# Ver documentación interactiva de la API
# http://localhost:8000/docs
```
