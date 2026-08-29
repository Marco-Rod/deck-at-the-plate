"""
Tácticas de juego (funciones puras)
====================================
- resolve_bunt: Resuelve el intento de toque de bola (sacrificio).
- resolve_steal: Resuelve un intento de robo de base según control/velocidad
  del pitcher contra la probabilidad base de robo en MLB (~68%).
- activate_tactic: Valida y aplica el uso de una carta táctica sobre el
  estado del juego (regla compartida con cualquier cliente/CPU).
"""
from typing import Tuple
import random

from app.core.enums import Event, RunnerBase
from app.core.engine_types import BatterAttrs, PitcherAttrs, Runners
from app.engine.deck_manager import discard_used_tactic
from app.engine.game_rules import EXTRA_INNINGS_MIN_INNING


def resolve_bunt(
    pitcher_attrs: PitcherAttrs,
    batter_attrs: BatterAttrs,
    runners: Runners,
) -> Tuple[Event, str, bool]:
    """
    Resuelve el toque de bola (Bunt).
    Ofrece una alta probabilidad de Out para el bateador (Sacrificio),
    a cambio de un 75% de éxito para avanzar a los corredores en base.
    
    Retorna: (event, description, sacrifice_success)
    """
    ctl = pitcher_attrs.get("control", 50)
    con = batter_attrs.get("contacto", 50)

    # Probabilidad de éxito del toque
    bunt_success_chance = 0.75 + (con - 50) * 0.003 - (ctl - 50) * 0.002
    bunt_success_chance = max(0.40, min(0.90, bunt_success_chance))

    if random.random() < bunt_success_chance:
        return Event.OUT_GROUND, "Toque de bola perfecto para toque de sacrificio. El bateador cae fuera en 1B pero los corredores avanzan.", True
    else:
        # Falló el toque: atrapado rápido en foul o ponche de toque
        return Event.STRIKE_LOOKING, "Toque defectuoso de foul.", False


def resolve_steal(
    pitcher_attrs: PitcherAttrs,
    runners: Runners,
    target_base: str,
) -> Tuple[bool, str]:
    """
    Resuelve el intento de robo de base (1B -> 2B o 2B -> 3B).
    Cruza la reacción/control del picher contra la velocidad base del juego.
    
    Retorna: (success, description)
    """
    if target_base not in (RunnerBase.SECOND, RunnerBase.THIRD):
        return False, "Base de destino no válida para robo."

    from_base = RunnerBase.FIRST if target_base == RunnerBase.SECOND else RunnerBase.SECOND
    if not runners.get(from_base):
        return False, f"No hay corredor en {from_base.upper()} para intentar el robo."

    ctl = pitcher_attrs.get("control", 50)
    vel = pitcher_attrs.get("velocidad", 50)

    # Probabilidad base de robo en MLB (~68% de éxito)
    steal_chance = 0.68 - (ctl * 0.002 + vel * 0.002)
    steal_chance = max(0.30, min(0.85, steal_chance))

    if random.random() < steal_chance:
        return True, f"¡Robo exitoso! El corredor se estafa la {target_base.upper()}."
    else:
        return False, f"¡Out en las bases! El receptor saca al corredor intentando robar la {target_base.upper()}."


def activate_tactic(
    state: dict,
    *,
    player_role: str,
    tactic_id: str,
    tactic_category: str,
    current_inning: int,
    is_top_inning: bool,
) -> Tuple[bool, str | None]:
    """
    Valida y aplica el uso de una carta táctica para el turno actual.

    La carta debe estar en la mano del jugador y, si pertenece a la categoría
    EXTRA_INNINGS, solo puede activarse desde la entrada
    ``EXTRA_INNINGS_MIN_INNING`` en adelante.

    Retorna ``(ok, code)``:
      - ``(True, None)``: la carta se activó (``state`` mutado).
      - ``(False, code)`` con ``code`` ∈ {"invalid_role", "not_in_hand", "extra_innings"}.
    """
    role = player_role.upper()
    if role == "BATTER":
        # En la Alta batea el visitante; en la Baja batea el local.
        player_key = "away" if is_top_inning else "home"
        role_key = "batter"
    elif role == "PITCHER":
        player_key = "home" if is_top_inning else "away"
        role_key = "pitcher"
    else:
        return False, "invalid_role"

    tactics_data = state.get("tactics", {}).get(player_key, {})
    player_hand = tactics_data.get("hand", [])

    if tactic_id not in player_hand:
        return False, "not_in_hand"

    if tactic_category == "EXTRA_INNINGS" and current_inning < EXTRA_INNINGS_MIN_INNING:
        return False, "extra_innings"

    active_tactics = state.get("active_tactics", {"home": None, "away": None})
    active_tactics[role_key] = tactic_id
    state["active_tactics"] = active_tactics

    discard_used_tactic(state["tactics"], player_key, tactic_id)
    return True, None