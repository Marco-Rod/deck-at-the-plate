"""
Tactics: acumulador de efectos (lógica pura)
============================================
Interpreta la lista ``effects`` de una TacticCard y la acumula sobre un dict
de modificadores listo para ``calculate_play_outcome``.

Reglas actuales (conservadas de gameplay._apply_tactic_modifiers):
  - Carta táctica de BATEADOR: effect.attribute ∈ {vision, contacto, poder}
  - Carta táctica de PÍCHER:   effect.attribute ∈ {movimiento}

Este módulo no consulta la BD: recibe los effects ya cargados.
"""
from typing import Any, Dict, List

from app.core.engine_types import TacticsModifiers

# Modificadores base del diccionario que espera calculator.py
_DEFAULT_MODIFIERS: TacticsModifiers = {
    "batter_con": 1.0,
    "batter_pwr": 1.0,
    "batter_vis": 1.0,
    "pitcher_mov": 1.0,
}


def new_default_tactic_modifiers() -> TacticsModifiers:
    """Devuelve un dict nuevo (sin alias) con los modificadores neutros."""
    return dict(_DEFAULT_MODIFIERS)


def accumulate_tactic_effects(
    effects: List[Dict[str, Any]],
    mods: TacticsModifiers = None,
    *,
    is_pitcher_tactic: bool = False,
) -> TacticsModifiers:
    """
    Acumula los effects de una carta táctica sobre ``mods`` (o uno nuevo).

    Args:
        effects: Lista de dicts {"attribute": str, "value": int} de la carta.
        mods:    Dict de modificadores a mutar (opcional; si se omite, uno nuevo).
        is_pitcher_tactic: True ⇒ la carta es del lanzador (solo "movimiento").

    Returns:
        El mismo dict ``mods`` acumulado (para encadenamiento).
    """
    mods = mods if mods is not None else new_default_tactic_modifiers()

    if is_pitcher_tactic:
        for eff in effects:
            attr = eff.get("attribute")
            val = eff.get("value", 0) / 100.0
            if attr == "movimiento":
                mods["pitcher_mov"] += val
    else:
        for eff in effects:
            attr = eff.get("attribute")
            val = eff.get("value", 0) / 100.0
            if attr == "vision":
                mods["batter_vis"] += val
            elif attr == "contacto":
                mods["batter_con"] += val
            elif attr == "poder":
                mods["batter_pwr"] += val

    return mods