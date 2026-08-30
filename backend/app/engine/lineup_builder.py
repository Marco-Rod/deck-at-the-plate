"""
Constructor del lineup ideal (lógica pura)
===========================================
Dado un conjunto de cartas (normalmente las del Starter Pack), construye el
mapa de slots del lineup ideal: ``{"P": card_id, "C": card_id, ...}``.

Sin acceso a base de datos: reproduce la heurística del PWA
``MyTeamPage.autoAssignLineup`` para que el jugador tenga un lineup válido
desde la entrega del sobre inicial.
"""

from typing import Collection, Dict, Sequence

from app.core.enums import PITCHER_POSITIONS

# Orden de los slots del campo. "P" y "DH" se resuelven aparte:
#   - "P": se cubre con la mejor carta lanzadora (PITCHER_POSITIONS o two-way).
#   - "DH": se cubre con la mejor carta no lanzadora disponible (cualquier
#     jugador de cuadro/jardín) o con un two-way aunque ya esté usada.
FIELD_SLOT_ORDER: Sequence[str] = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]


def _is_pitcher(card: object) -> bool:
    """Determina si una carta puede lanzar (posiciones de pitcher o two-way)."""
    return card.position in PITCHER_POSITIONS or bool(getattr(card, "is_two_way", False))


def _is_two_way(card: object) -> bool:
    return card.position == "TWP" or bool(getattr(card, "is_two_way", False))


def _best_card(cards: Collection, predicate) -> object | None:
    """Devuelve la carta con mayor ``overall`` que cumpla el predicado."""
    best = None
    for card in cards:
        if not predicate(card):
            continue
        if best is None or card.overall > best.overall:
            best = card
    return best


def build_optimal_lineup(cards: Collection) -> Dict[str, str]:
    """
    Construye el lineup ideal (slot → card id) a partir de un conjunto de cartas.

    Args:
        cards: Cartas disponibles (generalmente las 13 del Starter Pack).

    Returns:
        Mapa ``{slot: card_id}`` con los slots que fue posible cubrir.
    """
    used = set()
    slots: Dict[str, str] = {}

    # 1. Slots del campo: la mejor carta sin usar de la posición exacta.
    for slot in FIELD_SLOT_ORDER:
        best = _best_card(
            cards,
            lambda c, s=slot: c.id not in used and c.position == s,
        )
        if best is not None:
            slots[slot] = best.id
            used.add(best.id)

    # 2. P: la mejor carta lanzadora sin usar.
    pitcher = _best_card(
        cards,
        lambda c: c.id not in used and _is_pitcher(c),
    )
    if pitcher is not None:
        slots["P"] = pitcher.id
        used.add(pitcher.id)

    # 3. DH: la mejor carta no lanzadora (cualquier fielder) sin usar, o un
    #    two-way aunque ya esté usada en otro slot.
    dh = _best_card(
        cards,
        lambda c: (not _is_pitcher(c) or _is_two_way(c))
        and (c.id not in used or _is_two_way(c)),
    )
    if dh is not None:
        slots["DH"] = dh.id

    return slots