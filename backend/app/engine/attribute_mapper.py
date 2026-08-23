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
        (vision no existe como columna; se deriva del overall del bateador)
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.card import PlayerCardModel


def map_card_to_pitcher_attrs(card: "PlayerCardModel") -> dict:
    """
    Convierte un PlayerCardModel a un diccionario de atributos de pitcheo
    listo para ser consumido por el engine (calculator.py, fatigue_manager.py).

    Args:
        card: Instancia de PlayerCardModel obtenida de la base de datos.

    Returns:
        dict con claves: "velocidad", "control", "movimiento"
    """
    return {
        "velocidad": card.velocity,
        "control": card.control,
        "movimiento": card.movement,
    }


def map_card_to_batter_attrs(card: "PlayerCardModel") -> dict:
    """
    Convierte un PlayerCardModel a un diccionario de atributos de bateo
    listo para ser consumido por el engine (calculator.py).

    La "vision" del bateador se aproxima al promedio de contact y overall,
    ya que representa su capacidad de leer el lanzamiento entrante.

    Args:
        card: Instancia de PlayerCardModel obtenida de la base de datos.

    Returns:
        dict con claves: "contacto", "poder", "vision"
    """
    # Vision: capacidad de leer lanzamientos. Se aproxima como promedio
    # ponderado de contacto (70%) y overall (30%).
    vision = int(card.contact * 0.70 + card.overall * 0.30)

    return {
        "contacto": card.contact,
        "poder": card.power,
        "vision": vision,
    }
