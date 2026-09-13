"""Materializa y persiste la edición candidata ratings-2.0 + sus perfiles.

Réplica 1:1 del flujo dry-run ``audit_catalog_substitution.py`` (que CORRE a
806/23 con 12 gates OK y hace rollout al final), pero: (a) find-or-create
IDEMPOTENTE de la edición base candidata ``2026_BASE`` / ``edition-2.0`` con las
tres policies BASE; (b) SIN rollback — los ``db.commit()`` internos de los
servicios caen en savepoints (patrón audit) y el cierre lo decide el caller
(CLI ``materialize-card-catalog-candidate`` hace ``conn.commit()`` real).

Solo materializa la edición + distribuciones + CardGenerationProfile + 
CardRatingProfile. NO publica el catálogo: el candidato queda VALIDATING es
responsabilidad del comando ``publish-card-catalog`` (§22 two-phase), que al
encontrar el ACTIVE v1 legacy de OTRA edición deja el candidato VALIDATING con
el v1 ACTIVE intacto.

Idempotencia garantizada por:
    - edición: unique (season, code, version) find-or-create.
    - distribuciones: find-or-update por identidad (build_overall_rating_distribution).
    - CardGenerationProfile: unique (player_ratings_id, rating_model_version).
    - CardRatingProfile: unique (source_player_ratings_id, card_edition_id).
"""
import json
from datetime import date
from decimal import Decimal

from etl.config.performance_tier_2 import PERFORMANCE_TIER_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.base_eligibility_policy import BASE_ELIGIBILITY_POLICY_VERSION
from etl.services.card_rating_policies import BASE_RATING_POLICY_VERSION
from etl.services.card_rating_profiles import generate_card_rating_profile
from etl.services.rarity_policies import RARITY_POLICY_VERSION
from etl.services.rating_distributions import build_overall_rating_distribution
from etl.services.ratings2_card_profiles import generate_card_profile_from_ratings2

RATING_MODEL_VERSION_2 = "ratings-2.0"
DISTRIBUTION_VERSION_2 = "dist-1.0"

EDITION_CODE = "2026_BASE"
EDITION_VERSION = "edition-2.0"
EDITION_NAME = "2026 Base ratings-2.0 (candidata)"
SOURCE_TYPE = "SYSTEM"
EDITION_TYPE = "BASE"
STATUS_KIND = "VALIDATABLE"


def _json_default(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(
        f"cannot serialize {type(value).__name__}: {value!r}"
    )


def materialize_card_catalog_candidate(
    db,
    *,
    season: int,
    data_start_date: date,
    data_end_date: date,
    rating_model_version: str = RATING_MODEL_VERSION_2,
    source_distribution_version: str = DISTRIBUTION_VERSION_2,
    performance_tier_model_version: str = PERFORMANCE_TIER_MODEL_VERSION,
):
    """Persiste edición candidata + distribuciones + generation/rating profiles.

    El caller aborta o commitea. Devuelve el report con los conteos (misma
    forma que el audit, sin la sección dry-run de baselines).
    """
    from app.models import (
        CardCatalog,
        CardEdition,
        CardEditionSourceType,
        CardEditionType,
        CardGenerationProfile,
        CardRatingProfile,
        PlayerCardModel,
        PlayerRatings,
        RatingDistribution,
    )

    report: dict = {}

    # ---- 0. baseline real: ACTIVE v1 legacy intacto -------------------------
    active = (
        db.query(CardCatalog)
        .filter_by(
            season=season,
            edition_type=CardEditionType.BASE,
            status="ACTIVE",
        )
        .first()
    )
    if active is None:
        raise RuntimeError("no hay catálogo ACTIVE BASE; baseline roto")
    legacy_cards = (
        db.query(PlayerCardModel).filter_by(catalog_id=active.id).count()
    )
    report["baseline"] = {
        "catalog_id": str(active.id),
        "catalog_version": active.version,
        "status": active.status,
        "rating_model_version": active.rating_model_version,
        "cards": legacy_cards,
    }

    # ---- 1. edición candidata find-or-create (idempotente) -----------------
    candidate_edition = (
        db.query(CardEdition)
        .filter_by(
            season=season,
            code=EDITION_CODE,
            version=EDITION_VERSION,
        )
        .one_or_none()
    )
    if candidate_edition is None:
        candidate_edition = CardEdition(
            code=EDITION_CODE,
            name=EDITION_NAME,
            edition_type=CardEditionType.BASE,
            season=season,
            version=EDITION_VERSION,
            rating_policy_version=BASE_RATING_POLICY_VERSION,
            rarity_policy_version=RARITY_POLICY_VERSION,
            eligibility_policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
            source_type=CardEditionSourceType.SYSTEM,
            is_active=True,
            metadata_payload={},
        )
        db.add(candidate_edition)
        db.flush()
    report["candidate_edition"] = {
        "id": str(candidate_edition.id),
        "code": candidate_edition.code,
        "version": candidate_edition.version,
        "edition_type": candidate_edition.edition_type.value
        if hasattr(candidate_edition.edition_type, "value")
        else str(candidate_edition.edition_type),
    }

    # ---- 2. distribuciones por role (ratings-2.0, dist-1.0) -----------------
    distributions = {}
    for role in ("BATTER", "PITCHER"):
        dist_result = build_overall_rating_distribution(
            db,
            season=season,
            role=role,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            source_distribution_version=source_distribution_version,
            performance_tier_model_version=performance_tier_model_version,
        )
        dist = db.get(RatingDistribution, dist_result.rating_distribution_id)

        distributions[role] = {
            "status": getattr(dist_result, "status", "OK"),
            "population_size": dist_result.population_size,
            "min": dist.minimum,
            "max": dist.maximum,
        }
    report["candidate_distributions"] = distributions

    # ---- 3. CardGenerationProfile ratings-2.0 -------------------------------
    ratings_rows = (
        db.query(PlayerRatings)
        .filter_by(
            season=season,
            rating_model_version=rating_model_version,
            distribution_version=source_distribution_version,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
        )
        .all()
    )
    generated_ids = []
    for row in ratings_rows:
        result = generate_card_profile_from_ratings2(
            db, player_ratings_id=row.id
        )
        if getattr(result, "card_generation_profile_id", None):
            generated_ids.append(result.card_generation_profile_id)

    # ---- 4. CardRatingProfile sobre la edición candidata -------------------
    rating_profile_ids = []
    profiles = (
        db.query(CardGenerationProfile)
        .filter(CardGenerationProfile.id.in_(generated_ids))
        .all()
    )
    for profile in profiles:
        result = generate_card_rating_profile(
            db,
            source_player_ratings_id=profile.player_ratings_id,
            card_edition_id=candidate_edition.id,
        )
        rating_profile_ids.append(result.card_rating_profile_id)

    report["candidate_profiles"] = {
        "rating_rows": len(ratings_rows),
        "generation_profiles": len(generated_ids),
        "rating_profiles": len(rating_profile_ids),
    }
    return report


def main(argv=None) -> int:
    """```
    Persiste edición candidata ratings-2.0 (edition-2.0) + perfiles reales.

    Usa exactamente el patrón de sesión del audit (conn.begin + Session con
    join_transaction_mode="create_savepoint") pero CERRANDO con conn.commit()
    real: el commit atómico convierte los savepoints internos en la edición,
    distribuciones y perfiles persistidos de forma idempotente (re-runnable).
    ```
    """
    import argparse

    from sqlalchemy.orm import Session

    from app.database import engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--data-start-date", dest="data_start_date", type=date.fromisoformat, required=True)
    parser.add_argument("--data-end-date", dest="data_end_date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--rating-model",
        dest="rating_model_version",
        type=str,
        default=RATING_MODEL_VERSION_2,
    )
    parser.add_argument(
        "--distribution-version",
        dest="source_distribution_version",
        type=str,
        default=DISTRIBUTION_VERSION_2,
    )
    args = parser.parse_args(argv)

    with engine.connect() as conn:
        conn.begin()
        db = Session(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            report = materialize_card_catalog_candidate(
                db,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                rating_model_version=args.rating_model_version,
                source_distribution_version=args.source_distribution_version,
            )
        except Exception as exc:  # noqa: BLE001 - el CLI reporta y aborta
            conn.rollback()
            print(json.dumps({"error": repr(exc)}, default=_json_default, indent=2))
            return 1
        else:
            conn.commit()
    print(json.dumps(report, default=_json_default, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
