"""
Tácticas de juego (funciones puras)
====================================
- resolve_bunt: Resuelve el intento de toque de bola (sacrificio).
- resolve_steal: Resuelve un intento de robo de base según control/velocidad
  del pitcher contra la probabilidad base de robo en MLB (~68%).
"""
from typing import Tuple
import random

from app.core.enums import Event, RunnerBase
from app.core.engine_types import BatterAttrs, PitcherAttrs, Runners


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