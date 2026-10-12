# Fase 1 · Inventario de consumidores y rutas legacy

**Gate que cierra:** *"Mapa de dependencias y rutas legacy; ningún consumidor
crítico sin dueño/fuente identificada"* (plan maestro, secciones 17-18).

**Estado del gate:** CERRADO (el mapa es un contrato ejecutable en
`backend/tests/test_phase1_consumer_inventory.py`, 7 tests verdes).

---

## Arquitectura de gameplay por capas

```
REST/WS (routers)  ->  Services / Repositories  ->  Engine (lógica pura)  ->  Models (SQLAlchemy)
   auth, cards, games, gameplay, shop, user,   |      calculators/transitions        +  Postgres
   teams, ws (vive en routers)                 v      (sin IO, determinista)
```

- **Engine** = lógica pura sin FastAPI/BD/broadcast (`calculator`, `runner_manager`,
  `state_manager`, `turn_guard`, `fatigue_manager`, `steal_actions`,
  `tactical_actions`, `game_over_manager`, `fog_of_war`, `attribute_mapper`,
  `lineup_builder`, `player_stats_formatter`, `starter_pack`, `deck_manager`,
  `cpu_ai`, `bullpen`, `game_rules`, `game_actions`).
- **Routers** = Unit of Work: validan turno (REST), llaman al engine, persisten
  (commit) y **luego** emiten el broadcast WS.
- **Repositories/Services** = únicos que tocan BD por tema (card, game, stats,
  telemetry, user, team, pack, card_editions).

## Consumidores del catálogo de cartas (dueño = módulo de primer contacto)

| Consumidor | Qué consume | Owner (fuente de verdad) |
|---|---|---|
| `repositories/card_repository.py` | catálogo **ACTIVE / pack-eligible** (find_all_cards + fallback) | ETL catálogo (editions/ratings-2.0) |
| `services/pack_service.py` | open-pack/starter-pack; explícito: *jamás legacy/semillas/retirados* | catálogo ACTIVE |
| `services/game_session_service.py` | inicio de sesión, lineup, box-score (compat `GameEventLog`) | sesión 1v1 |
| `services/card_presenter.py` | payloads `build_pitcher_payload`/`build_batter_payload` | carta |
| `engine/starter_pack.py` | starter por posiciones (`REQUIRED_POSITIONS`) | catálogo ACTIVE |
| `engine/attribute_mapper.py` | carta -> `PitcherAttrs`/`BatterAttrs` | carta/catálogo |
| `engine/lineup_builder.py` | lineup óptimo posición real | carta |
| `engine/player_stats_formatter.py` | stats a box-score | stats de juego |
| `repositories/game_stats_repository.py` | box-score, stats por jugador, telemetría | eventos de la sesión |
| `repositories/pitch_telemetry_repository.py` | telemetría por pitch | pitch_log |

## Contrato REST/WS inventariado (28 REST + 1 WS)

- **auth**: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`.
- **cards**: `GET /api/v1/cards/teams`, `GET /api/v1/cards/teams/{team_id}`, `GET /api/v1/cards/{card_id}`.
- **teams**: `GET /api/v1/teams/cpu`.
- **shop**: `POST /api/v1/shop/starter-pack`, `POST /api/v1/shop/open-pack`.
- **games**: `POST /games/create`, `GET /games/{id}`, `GET /games/{id}/box-score`, `GET /games/{id}/player/{pid}/stats`.
- **gameplay** (`/api/v1/games`): `POST /{id}/pitch`, `POST /{id}/swing`, `POST /{id}/steal`, `POST /{id}/play-tactic`, `POST /{id}/change-pitcher`, `GET /{id}/available-pitchers`, `GET /{id}/rival-available-pitchers`, `POST /{id}/acknowledge-pitcher-change`.
- **user**: `GET/PUT /me/lineup`, `POST /me/team`, `GET /me/team`, `PUT /me/team/franchise`, `GET /me/team-stats`, `GET /me/profile`, `GET /me/inventory`.
- **ws**: `WS /ws/games/{game_id}`.

El test `test_no_hay_endpoints_indocumentados_en_los_routers` obliga a declarar
cualquier endpoint nuevo en el inventario (o falla), y el inverso detecta rutas
bajadas.

## WebSocket

- **Server→client** (broadcast, 7 tipos): `INIT_GAME_STATE`, `ERROR`,
  `PITCH_COMMITTED`, `PLAY_RESOLVED` (con `event` final), `PITCHER_CHANGED`,
  `PITCHER_CHANGE_ACKNOWLEDGED`, `STEAL_RESOLVED`.
- **Client→server**: el loop mantiene la conexión viva y **descarta el
  contenido** de los mensajes; todos los comandos pasan por REST (criterio de
  diseño auditado, relevante para la Fase 5: si el cliente solo habla por REST,
  la atomicidad se mide ahí).
- Fog of war: `state_data` sanitizado por destinatario en todos los broadcast.

## Rutas legacy (sobreviven o se migran con decisión)

1. `app/models.py` — shim de compatibilidad ("NO agregar definiciones aquí");
   el paquete `app/models/` es la fuente real.
2. `app/simulate_game.py::MockGameSession` — simulador en memoria fuera del motor.
3. `app/seeds/seed_cards.py::INITIAL_CARDS` — 28 cartas semilla no-catálogo.
4. `app/seeds/backfill_cards.py::LEGACY_MODEL_VERSION = "LEGACY"` — firma del
   backfill para cartas sin `rating_model_version`.
5. `app/seeds/seed_real_data_2025.py` — flujo pre-catálogo (PlayerCard.attributes JSON).
6. `PlayerCard.rating_model_version` nullable — compatibilidad con legacy
   (Fase 7 exigirá migrar semillas antes de volverla NOT NULL).

**Ningún consumidor crítico quedó huérfano**: cada módulo crítico tiene
fuente identificada, y los legacy están marcados y con test que pide
decisión explícita antes de tocarlos.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend/tests/test_phase1_consumer_inventory.py` | **Nuevo** — inventario dependency-checkable (rutas, engine, WS, legacy, consumidores) |
| `FASE_1_CONSUMIDORES.md` | Este reporte |