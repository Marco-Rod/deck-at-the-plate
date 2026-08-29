"""
Presenters de cartas
====================
Convierten una PlayerCardModel (ORM) en el dict JSON que consume el frontend
(vía HTTP o WebSocket). Centraliza el formato de tarjeta que antes estaba
duplicado en gameplay.py (payloads de pitcher/bateador activos, cambios de
pitcher, listas de bullpen).
"""
from typing import Any, TYPE_CHECKING

from app.engine.player_stats_formatter import format_player_stats

if TYPE_CHECKING:
    from app.models.card import PlayerCardModel


def build_card_base(card: "PlayerCardModel") -> dict:
    """
    Campos comunes de cualquier carta de jugador.
    """
    return {
        "id": card.id,
        "name": card.name,
        "number": card.number,
        "overall": card.overall,
        "position": card.position,
        "rarity": card.rarity.value if card.rarity else "COMMON",
        "team": card.team.name if card.team else "UNKNOWN",
    }


def build_pitcher_payload(
    card: "PlayerCardModel",
    *,
    with_repertoire: bool = False,
    with_stamina: bool = False,
    pitch_count: int = 0,
    fatigue_level: float = 0.0,
    already_used: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> dict:
    """
    Payload de un lanzador para el cliente.

    - with_repertoire: incluye el repertorio (necesario para el pitch selector).
    - with_stamina: incluye pitch_count y fatigue_level (útil tras el cambio).
    - already_used: flag de bullpen ("ya lanzó en este partido").
    - extra: campos adicionales arbitrarios.
    """
    payload = build_card_base(card)
    payload["stats"] = format_player_stats(card, "PITCHER")
    payload["role"] = "PITCHER"
    if with_repertoire:
        payload["repertoire"] = card.repertoire or []
    if with_stamina:
        payload["pitch_count"] = pitch_count
        payload["fatigue_level"] = fatigue_level
    if already_used is not None:
        payload["already_used"] = already_used
    if extra:
        payload.update(extra)
    return payload


def build_batter_payload(card: "PlayerCardModel", **extra: Any) -> dict:
    """
    Payload de un bateador para el cliente.
    """
    payload = build_card_base(card)
    payload["stats"] = format_player_stats(card, "BATTER")
    payload["role"] = "BATTER"
    if extra:
        payload.update(extra)
    return payload