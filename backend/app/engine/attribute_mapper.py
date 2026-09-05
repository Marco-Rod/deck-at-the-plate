"""
Módulo: attribute_mapper
========================
Convierte los atributos almacenados en la base de datos (columnas en inglés)
al formato de diccionario que espera el motor del juego (claves en español).

Por qué existe este módulo:
    El motor (calculator.py, fatigue_manager.py) fue diseñado con terminología
    en español para reflejar el contexto del juego. El modelo de base de datos
    usa inglés como convención estándar de backend. Este mapper es el único
    punto donde vive esa traducción, evitando duplicación y errores.

Mapeo de atributos:
    Pitcheo:
        velocity  → velocidad
        control   → control   (igual en ambos idiomas)
        movement  → movimiento

    Bateo:
        contact   → contacto
        power     → poder
        vision    → vision (columna persistida, backfill completado)
        clutch    → clutch
"""

from typing import TYPE_CHECKING

from app.core.engine_types import BatterAttrs, PitcherAttrs

if TYPE_CHECKING:
    from app.models.card import PlayerCardModel


def map_card_to_pitcher_attrs(card: "PlayerCardModel") -> PitcherAttrs:
    """
    Convierte un PlayerCardModel a un diccionario de atributos de pitcheo
    listo para ser consumido por el engine (calculator.py, fatigue_manager.py).

    Args:
        card: Instancia de PlayerCardModel obtenida de la base de datos.

    Returns:
        PitcherAttrs con claves: "velocidad", "control", "movimiento"
    """
    return {
        "velocidad": card.velocity,
        "control": card.control,
        "movimiento": card.movement,
    }


def map_card_to_batter_attrs(card: "PlayerCardModel") -> BatterAttrs:
    """
    Convierte un PlayerCardModel a un diccionario de atributos de bateo
    listo para ser consumido por el engine (calculator.py).

    La "vision" y el "clutch" son columnas persistidas (NOT NULL post-backfill)
    calculadas por seeds/backfill_cards.py, por lo que aquí no hay fallback.

    Args:
        card: Instancia de PlayerCardModel obtenida de la base de datos.

    Returns:
        BatterAttrs con claves: "contacto", "poder", "vision", "clutch"
    """
    return {
        "contacto": card.contact,
        "poder": card.power,
        "vision": card.vision,
        "clutch": card.clutch,
    }