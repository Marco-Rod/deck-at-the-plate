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
        stuff     → stuff      (contact-quality, 003B)

    Bateo:
        contact   → contacto
        power     → poder
        vision    → vision (columna persistida, backfill completado)
        clutch    → clutch
"""

from typing import TYPE_CHECKING

from app.core.engine_types import BatterAttrs, PitcherAttrs
from app.engine.stuff_policy import STUFF_BASELINE

if TYPE_CHECKING:
    from app.models.card import PlayerCardModel


def map_card_to_pitcher_attrs(card: "PlayerCardModel") -> PitcherAttrs:
    """
    Convierte un PlayerCardModel a un diccionario de atributos de pitcheo
    listo para ser consumido por el engine (calculator.py, fatigue_manager.py).

    ``stuff`` sale de la columna persistida (ratings-2.0 vía
    app/seeds/backfill_cards.py). Antes del backfill, una carta no puede tener
    NULL — la migración 0042 instala NOT NULL con server_default
    ``STUFF_BASELINE`` — así que aquí no hay fallback: el que exista es
    ``getattr(card, "stuff", STUFF_BASELINE)`` para objetos de test/duck-typing
    construidos a mano, que deben seguir siendo neutros en vez de crashing.

    Args:
        card: Instancia de PlayerCardModel obtenida de la base de datos.

    Returns:
        PitcherAttrs con claves: "velocidad", "control", "movimiento", "stuff"
    """
    return {
        "velocidad": card.velocity,
        "control": card.control,
        "movimiento": card.movement,
        "stuff": getattr(card, "stuff", STUFF_BASELINE),
    }


def map_card_to_batter_attrs(card: "PlayerCardModel") -> BatterAttrs:
    """
    Convierte un PlayerCardModel a un diccionario de atributos de bateo
    listo para ser consumido por el engine (calculator.py).

    La "vision" es una columna persistida y con señal real: ``calculator.py``
    la lee vía ``VISION_TAKE_WEIGHT``.

    El "clutch" se expone pero **no lo consume el motor** (GAMEPLAY-RATING-002,
    opción A): ``calculator.py`` lee sólo ``contacto``/``poder``/``vision``, y
    ``ratings-2.0`` no tiene datos situacionales para derivar Clutch
    (``clutch_evidence`` = 0 filas). La columna está materializada con el
    neutral explícito ``CLUTCH_NEUTRAL_RATING`` para que quede lista si se
    cablea, pero hoy es un placeholder inerte.

    Antes este docstring decía que vision y clutch venían de un backfill
    "NOT NULL post-backfill" sin fallback. Eso era falso para ambos en el
    catálogo ACTIVE: la ruta legacy `backfill_vision_clutch_edition` sólo toca
    cartas con ``rating_model_version IS NULL``, o sea no las de ``ratings-2.0``.

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