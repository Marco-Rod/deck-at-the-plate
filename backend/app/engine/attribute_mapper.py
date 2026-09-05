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
        vision    → vision (columna persistida tras backfill)
        clutch    → clutch
        (durante la transición, vision usa fallback legacy = 70% contact + 30% overall)
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


def _legacy_vision(card: "PlayerCardModel") -> int:
    """Fallback legacy: mismas fórmulas previas a la migración (transición).

    Solo aplica mientras las cartas existentes no tienen vision backfilleada.
    Replica exactamente la fórmula original para no alterar el gameplay.
    """
    return int(card.contact * 0.70 + card.overall * 0.30)


def map_card_to_batter_attrs(card: "PlayerCardModel") -> BatterAttrs:
    """
    Convierte un PlayerCardModel a un diccionario de atributos de bateo
    listo para ser consumido por el engine (calculator.py).

    La "vision" ahora es una columna persistida. Mientras existan cartas legacy
    sin backfill (vision aún no poblada), se usa un fallback equivalente a la
    fórmula original (70% contact + 30% overall), de modo que el resto de cartas
    se comporta igual que antes de la migración.

    Args:
        card: Instancia de PlayerCardModel obtenida de la base de datos.

    Returns:
        BatterAttrs con claves: "contacto", "poder", "vision", "clutch"
    """
    # Fase de compatibilidad (temporal): cartas legacy sin backfill.
    vision = card.vision if card.vision is not None else _legacy_vision(card)
    # Tras el backfill se eliminará el fallback y vision quedará NOT NULL.

    return {
        "contacto": card.contact,
        "poder": card.power,
        "vision": vision,
        "clutch": card.clutch if card.clutch is not None else 50,
    }