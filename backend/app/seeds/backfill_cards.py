"""
Backfill de columnas nuevas en player_cards (vision/clutch/stuff/edition_type)
=================================================================================
Migramos las cartas legacy a las columnas persistidas sin alterar la jugabilidad.

Contexto:
    En el ALTER (migración 0006) las columnas nuevas quedaron NOT NULL con
    server_default (vision=50, clutch=50, edition='BASE'). Por eso las cartas
    legacy ya tienen *algo* en esas columnas: placeholders. El backfill es el
    paso que les escribe los valores definitivos y los firma con un
    rating_model_version, que actúa de centinela de "ya backfilleada".

Qué hace con cada carta legacy (rating_model_version IS NULL):
    - vision: fórmula documentada en el documento de modelos (70% contact +
      30% overall), idéntica al fallback que usa el engine hoy. Aplicarla no
      cambia el gameplay de las cartas existentes → transición neutral.
    - clutch: neutral 50. El engine actual no lo consume; el valor real vendrá
      del pipeline de analytics del Matchup Engine V1.
    - stuff:rating-2.0 (player_ratings.stuff_rating), con STUFF_BASELINE (70)
      como neutral si el jugador no tiene corte de pitcheo. Ver abajo.
    - edition_type: 'BASE' (todos los legacy son base).
    - rating_model_version: 'LEGACY' (firma del backfill).
    - season: '2026' (catálogo actual del seed; la migración 0009 ya lo pobla).

El backfill de stuff (003B-6A)
-----------------------------
Stuff no es un placeholder neutral como vision/clutch: es un atributo que el
engine YA consume (suprime el power_score). Dejarlo en el server_default
haría que *toda* la flota de pitchers tuviera exactamente la supresión nula, es
decir, Stuff no existiría en las partidas reales aunque la política esté
integrada. Por eso se resuelve desde la fuente autoritativa, con esta
precedencia:

    1. card_rating_profiles.stuff_rating  (el corte con el que se publicó la
       carta — es la fuente que el propio card_presenter ya considera
       autoritativa para los atributos del rating)
    2. player_ratings.stuff_rating         (PITCHER, mismo player + season, el
       corte de ratings-2.0 más reciente por fecha de actualización)
    3. STUFF_BASELINE (70)                 (sin datos: neutro exacto, delta=0)

El paso 3 no es "un default silencioso": Stuff sin dato no puede emitir una
penalización inventada, y 70 es el valor de identidad que 003B-1 fijó para que
la supresión sea exactamente cero. Queda registrado en el resumen para poder
auditar cuántas cartas quedaron sin dato real.

Idempotente: solo toca cartas sin rating_model_version. Reejecutable sin daño.

Consejo operativo:
    Correr DESPUÉS de upgrade head y ANTES de activar el Matchup Engine V1.
    Hasta que se ejecute, el mapper conserva su fallback y nada cambia.
"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.engine.stuff_policy import STUFF_BASELINE
from app.models import PlayerCardModel

try:
    from app.models.card_rating_profile import CardRatingProfile
    from app.models.player_ratings import PlayerRatings
except ModuleNotFoundError:  # pragma: no cover - fallback de import
    from models.card_rating_profile import CardRatingProfile  # type: ignore
    from models.player_ratings import PlayerRatings  # type: ignore

try:
    from app.database import SessionLocal
except ModuleNotFoundError:
    from database import SessionLocal  # type: ignore

LEGACY_VISION_WEIGHT_CONTACT = 0.70
LEGACY_VISION_WEIGHT_OVERALL = 0.30
NEUTRAL_CLUTCH = 50
BASE_EDITION = "BASE"
LEGACY_MODEL_VERSION = "LEGACY"

PITCHER_ROLE = "PITCHER"


def _resolve_stuff_from_ratings(db, card) -> int:
    """Stuff de una carta desde ratings-2.0, con precedencia documentada.

    Devuelve ``(stuff, origen)`` para que el resumen de la migración sea
    auditable: una flota entera cayendo en el fallback neutro es un dato que
    hay que poder ver, no un detalle enterrado.
    """
    profile = (
        db.query(CardRatingProfile)
        .filter(CardRatingProfile.id == card.card_rating_profile_id)
        .first()
        if card.card_rating_profile_id
        else None
    )
    if profile is not None and profile.stuff_rating is not None:
        return int(profile.stuff_rating), "card_rating_profile"

    if card.player_id and card.season:
        rating = (
            db.query(PlayerRatings)
            .filter(
                PlayerRatings.player_id == card.player_id,
                PlayerRatings.season == card.season,
                PlayerRatings.role == PITCHER_ROLE,
                PlayerRatings.stuff_rating.isnot(None),
            )
            .order_by(PlayerRatings.updated_at.desc())
            .first()
        )
        if rating is not None:
            return int(rating.stuff_rating), "player_ratings"

    return STUFF_BASELINE, "neutral"


def backfill_vision_clutch_edition(db) -> dict:
    """Aplica el backfill a cartas sin rating_model_version y devuelve resumen.

    El nombre público histórico se conserva aunque el conjunto de columnas ya
    incluya ``stuff``: renombrarlo sólo para simetría obligaría a tocar tests y
    runbooks operativos por un cambio que no aporta nada funcional.
    """
    cards = db.query(PlayerCardModel).filter(
        text("rating_model_version IS NULL")
    ).all()

    stuff_sources = {"card_rating_profile": 0, "player_ratings": 0, "neutral": 0}

    for card in cards:
        card.vision = int(card.contact * LEGACY_VISION_WEIGHT_CONTACT + card.overall * LEGACY_VISION_WEIGHT_OVERALL)
        card.clutch = NEUTRAL_CLUTCH
        stuff, source = _resolve_stuff_from_ratings(db, card)
        card.stuff = stuff
        stuff_sources[source] += 1
        card.edition_type = BASE_EDITION
        card.rating_model_version = LEGACY_MODEL_VERSION

    db.commit()
    return {
        "total_legacy": len(cards),
        "updated": len(cards),
        "stuff_sources": stuff_sources,
    }


def main():
    db = SessionLocal()
    try:
        summary = backfill_vision_clutch_edition(db)
        print(f"Backfill completado: {summary['updated']} cartas actualizadas.")
        print(f"  Stuff por fuente: {summary['stuff_sources']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
