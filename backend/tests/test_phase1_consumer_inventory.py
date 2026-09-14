"""
Fase 1 · Inventario de consumidores y rutas legacy (mapa dependency-checkable).

Gate de la fase: *mapa de dependencias y rutas legacy; ningún consumidor
crítico sin dueño/fuente identificada* (plan maestro, secciones 17-18).

Este módulo convierte el mapa en un contrato ejecutable: el software evoluciona
y el inventario se actualiza a la vez, o el test señala el cambio con exactitud
(ruta/función/evento) para su revisión en el mismo PR.
"""

from __future__ import annotations

import inspect
import re
import typing
from pathlib import Path

from app.engine import (
    attribute_mapper,
    bullpen,
    calculator,
    cpu_ai,
    deck_manager,
    fatigue_manager,
    fog_of_war,
    game_actions,
    game_over_manager,
    lineup_builder,
    player_stats_formatter,
    runner_manager,
    starter_pack,
    state_manager,
    steal_actions,
    tactical_actions,
    turn_guard,
)
from app.routers import auth as router_auth
from app.routers import cards as router_cards
from app.routers import gameplay as router_gameplay
from app.routers import games as router_games
from app.routers import shop as router_shop
from app.routers import teams as router_teams
from app.routers import user as router_user
from app.routers import ws as router_ws

# ---------------------------------------------------------------------------
# 1. Rutas REST/WS activas (contrato servidor -> cliente)
# ---------------------------------------------------------------------------

EXPECTED_ROUTES = {
    # auth → identidad y sesión
    ("/api/v1/auth/register", "POST"),
    ("/api/v1/auth/login", "POST"),
    # cards → catálogo y rosters
    ("/api/v1/cards/teams", "GET"),
    ("/api/v1/cards/teams/{team_id}", "GET"),
    ("/api/v1/cards/{card_id}", "GET"),
    # teams → equipos CPU
    ("/api/v1/teams/cpu", "GET"),
    # shop → primer contacto con el catálogo
    ("/api/v1/shop/starter-pack", "POST"),
    ("/api/v1/shop/open-pack", "POST"),
    # games → sesión 1v1
    ("/api/v1/games/create", "POST"),
    ("/api/v1/games/{game_id}", "GET"),
    ("/api/v1/games/{game_id}/box-score", "GET"),
    ("/api/v1/games/{game_id}/player/{player_id}/stats", "GET"),
    # gameplay → motor 1v1 (mismo prefijo /api/v1/games)
    ("/api/v1/games/{game_id}/play-tactic", "POST"),
    ("/api/v1/games/{game_id}/pitch", "POST"),
    ("/api/v1/games/{game_id}/swing", "POST"),
    ("/api/v1/games/{game_id}/change-pitcher", "POST"),
    ("/api/v1/games/{game_id}/rival-available-pitchers", "GET"),
    ("/api/v1/games/{game_id}/available-pitchers", "GET"),
    ("/api/v1/games/{game_id}/acknowledge-pitcher-change", "POST"),
    ("/api/v1/games/{game_id}/steal", "POST"),
    # user → perfil, inventario, lineup y equipo del usuario
    ("/api/v1/user/me/profile", "GET"),
    ("/api/v1/user/me/inventory", "GET"),
    ("/api/v1/user/me/lineup", "GET"),
    ("/api/v1/user/me/lineup", "PUT"),
    ("/api/v1/user/me/team", "POST"),
    ("/api/v1/user/me/team", "GET"),
    ("/api/v1/user/me/team/franchise", "PUT"),
    ("/api/v1/user/me/team-stats", "GET"),
    # ws → live de partida
    ("/ws/games/{game_id}", "WS"),
}

ROUTER_OBJECTS = [
    router_auth.router,
    router_cards.router,
    router_teams.router,
    router_shop.router,
    router_games.router,
    router_gameplay.router,
    router_user.router,
    router_ws.router,
]


def _method_label(methods: typing.Optional[set[str]]) -> str:
    if methods is None:
        return "WS"
    return ",".join(sorted(methods))


def _actual_routes() -> set[tuple[str, str]]:
    actual: set[tuple[str, str]] = set()
    for router in ROUTER_OBJECTS:
        for route in router.routes:
            # APIRoute.path ya incluye el prefix del router en FastAPI
            actual.add((route.path, _method_label(getattr(route, "methods", None))))
    return actual


def test_todas_las_rutas_esperadas_del_mapa_existen():
    actual = _actual_routes()
    missing = EXPECTED_ROUTES - actual
    assert not missing, f"Rutas del inventario que ya no existen: {sorted(missing)}"


def test_no_hay_endpoints_indocumentados_en_los_routers():
    actual = _actual_routes()
    undocumented = actual - EXPECTED_ROUTES
    assert not undocumented, (
        f"Endpoints no declarados en el inventario (agregar a EXPECTED_ROUTES): {sorted(undocumented)}"
    )


# ---------------------------------------------------------------------------
# 2. Engine: funciones públicas consumidas por routers/servicios
# ---------------------------------------------------------------------------

ENGINE_FUNCTIONS = {
    attribute_mapper: ["map_card_to_pitcher_attrs", "map_card_to_batter_attrs"],
    bullpen: [
        "list_user_available_pitchers",
        "list_rival_available_pitchers",
        "perform_pitcher_change",
        "apply_human_pitcher_change",
        "acknowledge_pending_pitcher_change",
    ],
    calculator: ["calculate_play_outcome"],
    cpu_ai: ["get_cpu_pitch_action", "get_cpu_swing_action", "get_cpu_pitcher_change_decision", "is_cpu_turn"],
    deck_manager: ["initialize_tactics_state", "draw_card", "discard_used_tactic"],
    fatigue_manager: ["get_pitch_threshold", "compute_fatigue_level", "apply_pitcher_fatigue"],
    fog_of_war: ["sanitize_state_for_player"],
    game_actions: ["build_play_resolved_payload", "apply_tactic_modifiers", "resolve_swing", "execute_cpu_pitcher_change", "trigger_cpu_response"],
    game_over_manager: ["check_game_over"],
    lineup_builder: ["build_optimal_lineup"],
    player_stats_formatter: ["format_player_stats"],
    runner_manager: ["advance_runners"],
    starter_pack: ["select_starter_cards"],
    state_manager: ["end_half_inning", "process_at_bat_transition"],
    steal_actions: ["steal_attempt"],
    tactical_actions: ["activate_tactic", "resolve_bunt", "resolve_steal"],
    turn_guard: ["expected_actor", "is_player_turn"],
}


def test_funciones_publicas_del_engine_existen():
    missing = []
    for module, names in ENGINE_FUNCTIONS.items():
        for name in names:
            if not hasattr(module, name):
                missing.append(f"{module.__name__}.{name}")
    assert not missing, f"Funciones del inventario que ya no existen: {missing}"


# ---------------------------------------------------------------------------
# 3. WebSocket: eventos broadcast (server -> client)
# ---------------------------------------------------------------------------

WS_EVENTS_OUTBOUND = {
    # (evento, módulo que lo emite, origen)
    "INIT_GAME_STATE": (router_ws, "payload de bienvenida al conectar"),
    "ERROR": (router_ws, "partida inexistente"),
    "PITCH_COMMITTED": (router_gameplay, "router /{game_id}/pitch"),
    "PLAY_RESOLVED": (game_actions, "build_play_resolved_payload"),
    "PITCHER_CHANGED": (router_gameplay, "router /{game_id}/change-pitcher"),
    "PITCHER_CHANGE_ACKNOWLEDGED": (router_gameplay, "router /{game_id}/acknowledge-pitcher-change"),
    "STEAL_RESOLVED": (router_gameplay, "router /{game_id}/steal"),
}


def _module_source(module) -> str:
    file = Path(inspect.getsourcefile(module))
    return file.read_text(encoding="utf-8")


def test_ws_eventos_outbound_documentados_existen():
    missing = []
    for event, (module, origin) in WS_EVENTS_OUTBOUND.items():
        if f'"{event}"' not in _module_source(module):
            missing.append(f"{event} (emitido por {module.__name__}: {origin})")
    assert not missing, f"Eventos WS del inventario ya no se emiten: {missing}"


def test_ws_solo_broadcast_sin_comandos_entrantes():
    source = _module_source(router_ws)
    # El canal WS no consume comandos del cliente: mantiene la conexión viva y
    # los comandos se realizan por REST. Es un criterio de diseño auditado.
    assert "receive_text()" in source
    # Los payloads outbound usan el contrato JSON (send_json) sin inventar formato.
    assert "send_json" in source


# ---------------------------------------------------------------------------
# 4. Rutas y capas legacy (deben sobrevivir o migrarse con decisión explícita)
# ---------------------------------------------------------------------------

LEGACY_MARKERS = [
    "app.models: re-export de compatibilidad ('NO agregar definiciones aquí')",
    "app.simulate_game.MockGameSession: simulador en memoria fuera del motor real",
    "app.seeds.seed_cards.INITIAL_CARDS: 28 cartas semilla (no-catálogo)",
    "app.seeds.backfill_cards.LEGACY_MODEL_VERSION: cartas sin rating_model_version",
    "app.seeds.seed_real_data_2025: flujo pre-catálogo (PlayerCard.attributes JSON)",
    "PlayerCard.rating_model_version: nullable por compatibilidad legacy",
]


def test_marcas_legacy_identificadas_con_owner():
    from app.seeds import backfill_cards, seed_cards
    from app.simulate_game import MockGameSession  # noqa: F401

    assert len(seed_cards.INITIAL_CARDS) == 28, "dataset semilla legacy eliminado o alterado"
    assert backfill_cards.LEGACY_MODEL_VERSION == "LEGACY"

    from app.models import PlayerCardModel

    # app/models.py es un shim de compatibilidad; el paquete dirige imports
    # de verdad a app/models/. Verificar el archivo físico del shim.
    shim = Path(__file__).resolve().parent.parent / "app" / "models.py"
    text = shim.read_text(encoding="utf-8")
    assert "NO agregar definiciones aquí" in text
    assert "from app.models import" in text

    column = PlayerCardModel.__table__.c["rating_model_version"]
    assert column.nullable, "rating_model_version dejó de ser nullable: migrar semillas primero"


# ---------------------------------------------------------------------------
# 5. Consumidores críticos del catálogo (dueño = módulo de primer contacto)
# ---------------------------------------------------------------------------

CONSUMERS_CATALOG = {
    "app.repositories.card_repository": "catálogo ACTIVE/find_all_cards + fallback",
    "app.repositories.game_stats_repository": "box-score, stats por jugador, telemetría de eventos",
    "app.repositories.pitch_telemetry_repository": "telemetría por pitch (tipo/zona/resultado)",
    "app.services.pack_service": "open-pack / starter-pack (jamás legacy/semillas)",
    "app.services.game_session_service": "inicio de partida, lineup, box-score compat",
    "app.services.card_presenter": "serialización de cartas a payloads",
    "app.engine.starter_pack": "selección de starter (REQUIRED_POSITIONS)",
    "app.engine.attribute_mapper": "carta -> PitcherAttrs/BatterAttrs para el motor",
    "app.engine.lineup_builder": "lineup óptimo por posiciones reales",
    "app.engine.player_stats_formatter": "stats de jugador para box-score",
}


def test_consumidores_criticos_del_catalogo_tienen_dueño():
    import importlib

    missing = []
    for module_name, owner in CONSUMERS_CATALOG.items():
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001 - reportar para el mapa
            missing.append(f"{module_name} ({owner}): no importable -> {exc}")
    assert not missing, f"Consumidores sin dueño/carga: {missing}"