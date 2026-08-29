"""
Servicio: medias de equipo (OVR Bateo / Pitcheo / General)
============================================================
Fuente única del cálculo OVR que consumen los routers (teams.py, user.py).
Evita la fórmula duplicada: cualquier cambio de balance se hace aquí.
"""
from typing import Mapping, Sequence

from app.core.enums import PITCHER_POSITIONS


def _collapse(batter_overalls, pitcher_overalls, default: int) -> dict:
    bat_ovr = round(sum(batter_overalls) / len(batter_overalls)) if batter_overalls else default
    pit_ovr = round(sum(pitcher_overalls) / len(pitcher_overalls)) if pitcher_overalls else default
    overall = round((bat_ovr + pit_ovr) / 2)
    return {"overall": overall, "batOvr": bat_ovr, "pitOvr": pit_ovr}


def compute_team_ratings(cards: Sequence, default: int = 70) -> dict:
    """
    Medias a partir de cartas reales (PlayerCardModel).
    Acepta cualquier objeto con ``.overall`` y la regla ``is_pitcher``.
    """
    batters = [c.overall for c in cards if not c.is_pitcher]
    pitchers = [c.overall for c in cards if c.is_pitcher]
    return _collapse(batters, pitchers, default)


def compute_lineup_ratings(slots: Mapping[str, dict], default: int = 70) -> dict:
    """
    Medias a partir de ``UserLineup.slots`` (JSON): slot -> dict de carta.
    El slot ``"P"`` (dominio de lineup) cuenta como pitcher, igual que las
    posiciones lanzadoras de la carta (``PITCHER_POSITIONS``).
    """
    batters, pitchers = [], []
    for slot_pos, card in (slots or {}).items():
        if not card or not isinstance(card, Mapping):
            continue
        if card.get("position", "") in PITCHER_POSITIONS or slot_pos == "P":
            pitchers.append(card.get("overall", default))
        else:
            batters.append(card.get("overall", default))
    return _collapse(batters, pitchers, default)