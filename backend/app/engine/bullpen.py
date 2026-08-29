"""
Dominio: bullpen y cambios de pitcher
======================================
Reglas compartidas entre la sustitución de pitcher (humana y CPU) y la consulta
de relevistas disponibles. Aisladas del router HTTP (SRP): aquí NO hay
FastAPI HTTPException, ni commits (Unit of Work del router), ni prints de debug.

Responsabilidades:
    - ``list_user_available_pitchers`` : relevistas del inventario del usuario.
    - ``list_rival_available_pitchers`` : relevistas del equipo rival (CPU).
    - ``apply_human_pitcher_change``   : valida y ejecuta la sustitución humana.
    - ``acknowledge_pending_pitcher_change`` : confirma el cambio de la CPU y desbloquea.
"""
from typing import TYPE_CHECKING, List, Tuple

from app.engine.game_actions import perform_pitcher_change
from app.engine.game_rules import MIN_PITCHES_TO_CHANGE
from app.repositories import (
    find_pitchers_for_team,
    find_inventory_entry,
    find_user_inventory_pitchers,
    get_card_by_id,
)
from app.services.card_presenter import build_pitcher_payload

if TYPE_CHECKING:
    from app.models import GameSession


def _available_payloads(cards, pitch_counts: dict) -> List[dict]:
    """Payloads de relevistas marcando si ya lanzaron en esta partida."""
    used_pitcher_ids = set(pitch_counts.keys())
    return [
        build_pitcher_payload(card, already_used=card.id in used_pitcher_ids)
        for card in cards
    ]


def list_user_available_pitchers(
    db, game: "GameSession", state: dict, user_id: str
) -> List[dict]:
    """
    Relevistas del inventario del usuario, excluyendo el pitcher activo.
    """
    active_pitcher_id = state.get("active_pitcher")
    inventory_pitchers = find_user_inventory_pitchers(
        db,
        user_id=user_id,
        excluded_id=active_pitcher_id,
    )
    return _available_payloads(inventory_pitchers, state.get("pitch_counts", {}))


def list_rival_available_pitchers(
    db, game: "GameSession", state: dict
) -> Tuple[List[dict], str]:
    """
    Relevistas del equipo rival (su team_id se deriva de su pitcher de referencia),
    excluyendo el pitcher activo.

    Returns:
        (available_pitchers, error_message). ``error_message`` no vacío indica
        que no se pudo determinar el equipo rival (payload de error, no excepción).
    """
    active_pitcher_id = state.get("active_pitcher")
    user_role = state.get("user_role")  # 'HOME' o 'AWAY'
    rival_pitcher_id = (
        state.get("away_pitcher_id") if user_role == "HOME" else state.get("home_pitcher_id")
    )

    ref_pitcher = get_card_by_id(db, rival_pitcher_id)
    if not ref_pitcher or not ref_pitcher.team_id:
        return [], "No se pudo determinar el equipo rival"

    rival_pitchers = find_pitchers_for_team(
        db,
        team_id=ref_pitcher.team_id,
        excluded_id=active_pitcher_id,
    )
    return _available_payloads(rival_pitchers, state.get("pitch_counts", {})), ""


def apply_human_pitcher_change(
    db,
    game: "GameSession",
    state: dict,
    new_pitcher_id: str,
    is_home_user: bool,
    user_id: str,
) -> Tuple[str | None, str | None]:
    """
    Valida y ejecuta el cambio de pitcher del usuario.

    Returns:
        (old_pitcher_id, error_detail). ``error_detail`` no vacío indica una
        validación que el router traduce a HTTP 400.
    """
    # El pitcher no sólo debe existir: debe ser una carta que el jugador posee.
    # Sin esta comprobación un cliente podría enviar el ID de cualquier pitcher
    # del catálogo o del rival.
    if not find_inventory_entry(db, user_id, new_pitcher_id):
        return None, "No puedes usar un lanzador que no está en tu inventario."

    new_pitcher = get_card_by_id(db, new_pitcher_id)
    if not new_pitcher or not new_pitcher.is_pitcher:
        return None, (
            "La carta indicada no corresponde a un lanzador válido "
            "(SP, RP, CP, SU, CL o TWP)."
        )

    active_pitcher_id = state.get("active_pitcher")
    if new_pitcher_id == active_pitcher_id:
        return None, "El lanzador seleccionado ya está en el montículo."

    # La regla de disponibilidad es igual para humano y CPU: un pitcher que ya
    # lanzó en esta partida no puede volver a entrar.
    if new_pitcher_id in state.get("pitch_counts", {}):
        return None, "Ese lanzador ya participó en esta partida y no puede reingresar."

    current_pitch_count = (
        state.get("pitch_counts", {}).get(active_pitcher_id, 0) if active_pitcher_id else 0
    )
    if current_pitch_count < MIN_PITCHES_TO_CHANGE:
        return None, (
            f"El lanzador debe haber lanzado al menos {MIN_PITCHES_TO_CHANGE} pitches. "
            f"Lleva {current_pitch_count}."
        )

    old_pitcher_id = perform_pitcher_change(game, state, new_pitcher_id, is_home=is_home_user)
    return old_pitcher_id, None


def acknowledge_pending_pitcher_change(state: dict) -> bool:
    """
    Confirma el cambio de pitcher pendiente (decisión de la CPU) y desbloquea el juego.

    Returns:
        True si había un cambio pendiente por confirmar; False en caso contrario.
    """
    if not state.get("awaiting_pitcher_change_acknowledgment"):
        return False
    state["awaiting_pitcher_change_acknowledgment"] = False
    state["pending_pitcher_change"] = None
    return True
