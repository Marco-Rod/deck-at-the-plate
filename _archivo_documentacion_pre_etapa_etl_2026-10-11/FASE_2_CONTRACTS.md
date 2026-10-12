# Fase 2 — Contract tests REST del gameplay (gate cerrado)

**Estado:** ✅ VERDE — `tests/contract/` 56 tests + baseline completo (871 en total,
exit 0) en contenedor. Commit de fase: **(ver HEAD al cierre de la fase).**

---

## Gate de la Fase 2 (plan maestro)

> "Verificación por contrato (HTTP + WS outbound): cada endpoint de gameplay responde
> happy-path y negativos con el código HTTP documentado, el payload tiene la forma
> documentada, y los broadcast WS salen con el `type` documentado."

Resultado: **GATES CERRADOS**. No solo se verificó el contrato: los tests destaparon
**2 bugs de contrato reales** en el código de producción, ambos corregidos y
regresionados (detalles abajo).

## Harness (`tests/contract/`)

- `conftest.py`:
  - App FastAPI completa via `TestClient(app)` (starlette/httpx del contenedor).
  - `get_db` sobreescrito → SQLite in-memory compartida (`StaticPool`,
    `check_same_thread=False`): `seed_session` del tester y las sesiones de la API
    ven la misma BD.
  - Broadcasts WS capturados en memoria (monkeypatch de
    `manager.broadcast_to_game`/`broadcast_to_game_view` sobre la instancia
    singleton) → se asertan los eventos del contrato WS sin sockets reales.
  - Auth real (register → login OAuth2 form → Bearer JWT) en cada test.
  - Autouse: reset del rate-limit 429 de login (`auth._login_limits`) por test.
  - Factories: `register_user`, `roster_factory`, `game_factory` (1v1 PvE humano
    HOME vs CPU), `mutate_game` (editor de columnas/state_data sin pasar por API).

## Cobertura por endpoint

| Área | Happy | Negativos verificados |
|---|---|---|
| `POST /auth/register` | 201 + wallet 1000/0 | 409 duplicado; 422 payloads |
| `POST /auth/login` | 200 access_token | 401 malas creds / usuario inexistente |
| `GET /user/me/profile` | 200 | 401 sin token |
| `POST /games/create` | 201 campos mínimos | 403 owner distinto; 400 player_position; 500 CPU sin cartas; 401 sin token |
| `GET /games/{id}` | 200 + **fog-of-war** | 404; 403 ajeno |
| `GET /games/{id}/box-score` | 200 vacío | 403 ajeno |
| `GET /games/{id}/player/{pid}/stats` | 200 | — |
| `POST /games/{id}/pitch` | 200 + PITCH_COMMITTED + PLAY_RESOLVED | 403 fuera de turno; 400 repertorio; 422 zone ∉ 1-9; 404 partida; 403 cambio pendiente; IBB sin repertorio |
| `POST /games/{id}/swing` | 200 PLAY_RESOLVED + PITCH_COMMITTED | 403 fuera de turno (top); 403 cambio pendiente |
| `POST /games/{id}/steal` | 200 STEAL_RESOLVED (con corredor en 1B) | 403 ajeno |
| `POST /games/{id}/change-pitcher` | 200 PITCHER_CHANGED (inventario + pitch_count ≥ min) | 400 sin inventario; 400 ya activo; 409 pendiente; 403 fuera de turno |
| `GET /available-pitchers` / `rival-available-pitchers` | 200 con inventario / CPU | 403 ajeno; 404 partida |
| `POST /acknowledge-pitcher-change` | 200 sin cambio; 200 con desbloqueo + PITCHER_CHANGE_ACKNOWLEDGED | — |
| `POST /play-tactic` | 200 en mano | 400 fuera de mano; 404 carta; 400 extra-innings <10; 400 rol; 403 ajeno |

## Bugs reales encontrados y corregidos

### B1 — Bullpen rival roto (500): `find_pitchers_for_team(team_id=...)`

`app/engine/bullpen.py:67` (`list_rival_available_pitchers`) llamaba
`find_pitchers_for_team(db, team_id=ref.team_id, ...)`, pero la firma real es
`find_pitchers_for_team(db, team_ref, exclude_ids=None, excluded_id=None)`
(`app/repositories/card_repository.py:37`). Keyword desconocido → `TypeError` →
`GET /rival-available-pitchers` devolvía **500** siempre que había un pitcher
rival con team. 

**Fix:** pasar el team_id posicionalmente + `excluded_id`.
**Evidencia:** el test `test_bullpen_usuario_y_rival` fallaba con TypeError; pasó
tras el fix.

### B2 — Turn guard con bypass CPU: acciones humanas en media entrada de la CPU

`app/engine/turn_guard.py:is_player_turn`: con `expected == "CPU_BOT"` devolvía
`True` para CUALQUIER `user_id`. En PvE el humano podía:
- `swing` desde la Alta (cuando la CPU batea): el guard pasaba y el flujo llegaba
  al 400 "no hay picheo" en lugar del 403 de turno;
- `pitch`/`change-pitcher` desde la Baja (cuando la CPU pichea): 403 pasaba.

El motor de CPU usa su propia función (`cpu_ai.is_cpu_turn`), así que el bypass
del guard no tenía consumidores legítimos.

**Fix:** `if expected == "CPU_BOT": return user_id == expected` → solo el motor
(pasar `user_id="CPU_BOT"`) puede actuar en el turno del rival.
**Evidencia:** `test_swing_fuera_de_turno_top_403`, `test_pitch_fuera_de_turno_403`
y `test_change_pitcher_fuera_de_turno_403` pasaban solo con el fix.

## Decisiones de contrato documentadas

- **PvE normaliza `away_user_id = "CPU_BOT"`** en la sesión persistida, aunque el
  payload lleve el team_id de la CPU. `GET /games/{id}` no expone el uuid del team.
- **Fog of war** (PvE humano HOME): el picheo se enmascara al BATEADOR (media
  Baja). En la Alta el humano es el lanzador → ve su propio `current_pitch`.
  Forma enmascarada: `{"has_pitched": true, "pitch_type": null, "zone": null}`.
- **`pitch_type="IBB"`** es válido sin repertorio.
- **Una CPU media entrada no permitida**: `steal` NO tiene turn guard (solo
  pertenencia) — gap conocido, candidato a Fase 5.
- Fixtures ampliados: `publishable_player` (reuso de team, role/position, ratings
  condicionales `ck_player_ratings_complete_role_shape`, repertorio dict FF/SL/CH/CU)
  y `seed_roster` (equipo CPU 9 bateadores + 2 pitchers, catalog publicado).

## Checklist del gate

- [x] Candidates cubiertos happy + negativos con códigos esperados
- [x] Payloads con la forma documentada (respuesta de swing = `PlayResultResponse`)
- [x] Broadcast WS asertados por `type` en 5 flujos (PITCH_COMMITTED,
      PLAY_RESOLVED, STEAL_RESOLVED, PITCHER_CHANGED, PITCHER_CHANGE_ACKNOWLEDGED)
- [x] Baseline completo sigue verde (871 tests, exit 0)
- [x] Bugs B1 y B2 corregidos y regresionados