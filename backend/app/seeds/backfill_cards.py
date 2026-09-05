"""
Backfill de columnas nuevas en player_cards (vision/clutch/edition)
===================================================================
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
    - edition: 'BASE' (todos los legacy son base).
    - rating_model_version: 'LEGACY' (firma del backfill).

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
from app.models import PlayerCardModel

try:
    from app.database import SessionLocal
except ModuleNotFoundError:
    from database import SessionLocal  # type: ignore

LEGACY_VISION_WEIGHT_CONTACT = 0.70
LEGACY_VISION_WEIGHT_OVERALL = 0.30
NEUTRAL_CLUTCH = 50
BASE_EDITION = "BASE"
LEGACY_MODEL_VERSION = "LEGACY"


def backfill_vision_clutch_edition(db) -> dict:
    """Aplica el backfill a cartas sin rating_model_version y devuelve resumen."""
    cards = db.query(PlayerCardModel).filter(
        text("rating_model_version IS NULL")
    ).all()

    for card in cards:
        card.vision = int(card.contact * LEGACY_VISION_WEIGHT_CONTACT + card.overall * LEGACY_VISION_WEIGHT_OVERALL)
        card.clutch = NEUTRAL_CLUTCH
        card.edition = BASE_EDITION
        card.rating_model_version = LEGACY_MODEL_VERSION

    db.commit()
    return {"total_legacy": len(cards), "updated": len(cards)}


def main():
    db = SessionLocal()
    try:
        summary = backfill_vision_clutch_edition(db)
        print(f"Backfill completado: {summary['updated']} cartas actualizadas.")
    finally:
        db.close()


if __name__ == "__main__":
    main()