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

Stuff en catálogos publicados (DATA-STUFF-001B-2)
--------------------------------------------------
La ruta legacy de arriba NO cubre el catálogo ACTIVE BASE v2 (ratings-2.0):
esas cartas ya están firmadas con `rating_model_version='ratings-2.0'`, así que
el centinela `IS NULL` las salta. Y el defecto real era otro — la publicación
(`etl/services/card_catalog.py::_card_from_profile`) nunca asignó `stuff`, así
que las 806 cartas active quedaron todas en el `server_default` 70 mientras el
Stuff autoritativo de 392 de los 404 pitchers era otro valor.

    `python app/seeds/backfill_cards.py --catalog-stuff`            (dry-run)
    `python app/seeds/backfill_cards.py --catalog-stuff --apply`   (escribe)

`backfill_catalog_stuff()` reutiliza `_resolve_stuff_from_ratings()`, o sea la
misma precedencia de arriba, y sólo materializa cartas de role PITCHER:
`stuff_rating` es NULL por diseño para BATTER, así que la flota de bateo
permanece en STUFF_BASELINE (su valor exacto) en vez de recibir 402
"correcciones" inventadas.

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

from app.models.card_catalog import CardCatalog
from app.models.card_edition import CardEditionType
from etl.config.ratings_2 import CLUTCH_NEUTRAL_RATING

LEGACY_VISION_WEIGHT_CONTACT = 0.70
LEGACY_VISION_WEIGHT_OVERALL = 0.30
# GAMEPLAY-RATING-002: este literal era 50 y divergía de la constante canónica
# `CLUTCH_NEUTRAL_RATING` (70) que usa `etl/services/batter_clutch.py` y que ya
# materializan los batters de ratings-2.0. Dos neutrales distintos para el
# mismo placeholder; se colapsa en la fuente canónica.
NEUTRAL_CLUTCH = CLUTCH_NEUTRAL_RATING
BASE_EDITION = "BASE"
LEGACY_MODEL_VERSION = "LEGACY"

PITCHER_ROLE = "PITCHER"
BATTER_ROLE = "BATTER"


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


def backfill_catalog_stuff(db, catalog_id: str = None, apply: bool = False) -> dict:
    """DATA-STUFF-001B-2 -- materializa ``player_cards.stuff`` desde ratings-2.0.

    Corrige el silent default que encontró ``etl/audit_stuff_propagation.py``:
    la ruta de publicación nunca asignó ``stuff``, así que las 806 cartas del
    catálogo ACTIVE BASE v2 quedaron todas en el ``server_default`` 70 mientras
    el Stuff autoritativo de 392 de los 404 pitchers era otro valor. El motor
    aplicaba la política de 003B sobre un atributo que el catálogo silenciaba.

    Alcance:
        Un catálogo explícito (por defecto, el ACTIVE BASE de la temporada). No
        es un filtro global: un catálogo retirado sigue siendo histórico y no
        se reescribe.

    Rol:
        Sólo se materializan las cartas cuyo ``CardRatingProfile`` es
        PITCHER. ``stuff_rating`` es NULL por diseño para BATTER (CHECK de
        role-shape) y la columna de la carta es NOT NULL, así que la flota de
        bateo debe quedarse en ``STUFF_BASELINE``, que es su valor exacto
        (delta 0, supresión 0). Sin esta separación, contar o escribir las 806
        cartas produciría ~402 "correcciones" inventadas.

    Idempotencia:
        Escribir es ``card.stuff != autoritativo``; una segunda corrida con la
        misma fuente no toca ninguna fila. No usa el centinela
        ``rating_model_version IS NULL`` de la ruta legacy: esas cartas ya
        están firmadas y son otro caso.

    Seguridad:
        ``apply=False`` (default) sólo informa: calcula el plan y hace
        ``rollback``. Nada se escribe sin que se pida explícitamente.

    Returns:
        dict con el plan, los contadores por fuente y por clase, y una muestra
        de las cartas que cambiarían.
    """
    if catalog_id is None:
        catalog = (
            db.query(CardCatalog)
            .filter(
                CardCatalog.season == 2026,
                CardCatalog.edition_type == CardEditionType.BASE,
                CardCatalog.status == "ACTIVE",
            )
            .first()
        )
        if catalog is None:
            raise RuntimeError("no hay catálogo ACTIVE BASE para la temporada 2026")
        catalog_id = catalog.id

    cards = db.query(PlayerCardModel).filter(PlayerCardModel.catalog_id == catalog_id).all()

    profile_ids = {c.card_rating_profile_id for c in cards if c.card_rating_profile_id}
    profiles = {
        p.id: p
        for p in db.query(CardRatingProfile)
        .filter(CardRatingProfile.id.in_(profile_ids))
        .all()
    } if profile_ids else {}

    ratings = {}
    for rating in (
        db.query(PlayerRatings)
        .filter(
            PlayerRatings.season == 2026,
            PlayerRatings.role == PITCHER_ROLE,
            PlayerRatings.stuff_rating.isnot(None),
        )
        .order_by(PlayerRatings.updated_at.desc())
        .all()
    ):
        ratings.setdefault((rating.player_id, rating.season), rating)

    sources = {"card_rating_profile": 0, "player_ratings": 0, "neutral": 0}
    roles = {PITCHER_ROLE: 0, BATTER_ROLE: 0, "unknown": 0}
    changed = 0
    unchanged = 0
    delta_total = 0
    sample = []

    for card in cards:
        profile = profiles.get(card.card_rating_profile_id)
        rating = (
            ratings.get((card.player_id, card.season))
            if card.player_id and card.season
            else None
        )

        # El rol se infiere de la propia fuente autoritativa, no del `position`
        # de la carta: `position` es una etiqueta de presentación y un two-way
        # publica un único perfil.
        #   - CardRatingProfile presente  → su `role` manda.
        #   - sin perfil pero con PlayerRatings PITCHER → es pitcher (el query
        #     ya está filtrado por role=PITCHER, así que la fuente lo declara).
        #   - ninguna de las dos → no hay Stuff autoritativo: se deja el
        #     baseline y se reporta, nunca se inventa un valor.
        if profile is not None:
            role = profile.role
        elif rating is not None:
            role = PITCHER_ROLE
        else:
            role = "unknown"
        roles[role] = roles.get(role, 0) + 1

        if role != PITCHER_ROLE:
            # Batters se quedan en STUFF_BASELINE por contrato de role-shape.
            continue

        stuff, source = _resolve_stuff_from_ratings(db, card)
        sources[source] += 1

        if card.stuff == stuff:
            unchanged += 1
            continue

        changed += 1
        delta_total += stuff - card.stuff
        if len(sample) < 15:
            sample.append(
                {
                    "card_id": card.id,
                    "name": card.name,
                    "from": card.stuff,
                    "to": stuff,
                    "delta": stuff - card.stuff,
                    "source": source,
                }
            )
        if apply:
            card.stuff = stuff

    if apply:
        db.commit()
    else:
        db.rollback()

    return {
        "catalog_id": catalog_id,
        "apply": apply,
        "total_cards": len(cards),
        "pitcher_cards": roles.get(PITCHER_ROLE, 0),
        "batter_cards_untouched": roles.get(BATTER_ROLE, 0),
        "unknown_role_skipped": roles.get("unknown", 0),
        "stuff_sources": sources,
        "changed": changed,
        "unchanged": unchanged,
        "mean_delta": round(delta_total / changed, 4) if changed else 0.0,
        "sample": sample,
    }


def backfill_catalog_clutch(db, catalog_id: str = None, apply: bool = False) -> dict:
    """GAMEPLAY-RATING-002 (opción A) -- neutral de Clutch en cartas publicadas.

    Corrige un silent default de la misma familia que DATA-STUFF-001, pero con
    la dirección opuesta: Stuff tenía una fuente autoritativa real que no se
    estaba copiando; acá **no hay fuente**. ``clutch_evidence`` está vacío en
    ``ratings-2.0`` (0 de 869 filas) y el motor no lee Clutch, así que la
    decisión tomada es placeholder explícito y sin efecto de gameplay.

    Lo que sí estaba mal era el valor: ``clutch_rating`` es NULL por diseño para
    role PITCHER (CHECK de role-shape) y la publicación usaba ``or 0``, dejando
    a los 404 pitchers en el piso del dominio. 0 no es "sin dato", es el peor
    Clutch posible; si algún día se cablea (dirección B, leverage situacional)
    arrancaría en el peor valor del rango.

    Alcance:
        Un catálogo explícito (por defecto, el ACTIVE BASE). El catálogo
        retirado se deja histórico, igual que en ``backfill_catalog_stuff``.

    Sólo rellena ausencias, nunca pisa datos:
        Se escribe únicamente donde ``clutch_rating`` es NULL en la fuente
        autoritativa **y** la carta no tiene ya el neutral. Una carta con Clutch
        real (hoy no existe ninguna) queda intacta.

    Idempotente:
        Escribir es ``card.clutch != neutral``; la segunda corrida no toca filas.

    Seguridad:
        ``apply=False`` (default) calcula el plan y hace ``rollback``.

    Returns:
        dict con el plan, los conteos por rol y una muestra de los cambios.
    """
    if catalog_id is None:
        catalog = (
            db.query(CardCatalog)
            .filter(
                CardCatalog.season == 2026,
                CardCatalog.edition_type == CardEditionType.BASE,
                CardCatalog.status == "ACTIVE",
            )
            .first()
        )
        if catalog is None:
            raise RuntimeError("no hay catálogo ACTIVE BASE para la temporada 2026")
        catalog_id = catalog.id

    cards = db.query(PlayerCardModel).filter(PlayerCardModel.catalog_id == catalog_id).all()

    profile_ids = {c.card_rating_profile_id for c in cards if c.card_rating_profile_id}
    profiles = {
        p.id: p
        for p in db.query(CardRatingProfile)
        .filter(CardRatingProfile.id.in_(profile_ids))
        .all()
    } if profile_ids else {}

    # Fuente autoritativa: sólo importa si trae Clutch real. Si no lo trae, la
    # ausencia es legítima (role-shape de PITCHER) y se materializa el neutral.
    has_authoritative_clutch: dict[str, bool] = {}
    if profile_ids:
        for profile_id, has_value in (
            db.query(CardRatingProfile.id, CardRatingProfile.clutch_rating.isnot(None))
            .filter(CardRatingProfile.id.in_(profile_ids))
            .all()
        ):
            has_authoritative_clutch[profile_id] = bool(has_value)

    roles = {PITCHER_ROLE: 0, BATTER_ROLE: 0, "unknown": 0}
    changed = 0
    unchanged = 0
    skipped_with_data = 0
    sample = []

    for card in cards:
        profile = profiles.get(card.card_rating_profile_id)
        role = profile.role if profile is not None else "unknown"
        roles[role] = roles.get(role, 0) + 1

        if has_authoritative_clutch.get(card.card_rating_profile_id, False):
            # Hay Clutch autoritativo: nunca se pisa.
            skipped_with_data += 1
            continue

        if card.clutch == CLUTCH_NEUTRAL_RATING:
            unchanged += 1
            continue

        changed += 1
        if len(sample) < 15:
            sample.append(
                {
                    "card_id": card.id,
                    "name": card.name,
                    "role": role,
                    "from": card.clutch,
                    "to": CLUTCH_NEUTRAL_RATING,
                }
            )
        if apply:
            card.clutch = CLUTCH_NEUTRAL_RATING

    if apply:
        db.commit()
    else:
        db.rollback()

    return {
        "catalog_id": catalog_id,
        "apply": apply,
        "neutral": CLUTCH_NEUTRAL_RATING,
        "total_cards": len(cards),
        "pitcher_cards": roles.get(PITCHER_ROLE, 0),
        "batter_cards_untouched": roles.get(BATTER_ROLE, 0),
        "unknown_role_skipped": roles.get("unknown", 0),
        "skipped_with_authoritative_clutch": skipped_with_data,
        "changed": changed,
        "unchanged": unchanged,
        "sample": sample,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backfills de player_cards")
    parser.add_argument(
        "--catalog-stuff",
        action="store_true",
        help="DATA-STUFF-001B-2: materializar player_cards.stuff (dry-run)",
    )
    parser.add_argument(
        "--catalog-clutch",
        action="store_true",
        help="GAMEPLAY-RATING-002: neutral de Clutch en pitchers (dry-run)",
    )
    parser.add_argument(
        "--catalog-id", default=None, help="catálogo objetivo (por defecto, el ACTIVE BASE)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="escribir de verdad (sin esto, dry-run con rollback)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.catalog_stuff:
            import json

            summary = backfill_catalog_stuff(
                db, catalog_id=args.catalog_id, apply=args.apply
            )
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            if not args.apply:
                print(
                    "\nDRY-RUN: nada escrito. Reejecutar con --apply para materializar."
                )
            return

        if args.catalog_clutch:
            import json

            summary = backfill_catalog_clutch(
                db, catalog_id=args.catalog_id, apply=args.apply
            )
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            if not args.apply:
                print(
                    "\nDRY-RUN: nada escrito. Reejecutar con --apply para materializar."
                )
            return

        summary = backfill_vision_clutch_edition(db)
        print(f"Backfill completado: {summary['updated']} cartas actualizadas.")
        print(f"  Stuff por fuente: {summary['stuff_sources']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
