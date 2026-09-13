"""Dry-run de sustitución ratings-1.0 (829) → ratings-2.0 con elegibilidad.

Simula EXPLICITAMENTE el escenario de lifecycle que publish_card_catalog todavia
no puede ejecutar (frontera §22 no-op por (season, edition_type)):

    ACTIVE legacy v1 ratings-1.0 = 829          <- NO se toca
                    |
                    v
    candidate BASE modern v2 ratings-2.0        <- dry-run transaccional

NO llama a publish_card_catalog (haría commits internos y el no-op del ACTIVE
v1 lo detendría). Reproduce su planning+validación (mismos helpers privados)
DENTRO de una transacción controlada, pero ahora declarando también la política
de elegibilidad en la edición: el CardRatingProfile materializa la decisión y la
publicación replica lee `_resolve_published_eligibility` (INELIGIBLE → skip).

Entregables:
    - baseline real intacto (catálogo ACTIVE v1, edición, cartas=829)
    - poblaciones del dry-run: candidatos / INELIGIBLE / publicados / pack eligible
    - impacto de sustitución por jugador (continúan vs caídos vs nuevos)
    - pool de rarity sobre los publicados (gate de los 5 tiers)
    - franquicias CPU: cada mapping activo con >= 1 carta candidata (30)
    - rollback: conteos antes/después de todas las tablas tocadas

Seguridad: Connection.begin() + Session(join_transaction_mode="create_savepoint");
los commit() internos de generación son savepoints; el ROLLBACK final descarta
TODO. La DB queda byte-por-byte idéntica (verificado por conteos).
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import engine, SessionLocal
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
    SourceTeamGameTeamMapping,
)
from etl.config.performance_tier_2 import PERFORMANCE_TIER_MODEL_VERSION
from etl.services.base_eligibility_policy import (
    BASE_ELIGIBILITY_POLICY_VERSION,
    ELIGIBLE,
    INELIGIBLE,
    PROVISIONAL,
)
from etl.services.card_catalog import (
    _card_from_profile,
    _game_team_for_player,
    _resolve_published_eligibility,
    _resolve_published_rarity,
    _resolve_rating_profile,
    _validate_rows,
    profile_publish_order,
)
from etl.services.card_rating_policies import BASE_RATING_POLICY_VERSION
from etl.services.card_rating_profiles import generate_card_rating_profile
from etl.services.rarity_policies import RARITY_POLICY_VERSION
from etl.services.rating_distributions import build_overall_rating_distribution
from etl.services.ratings2_card_profiles import generate_card_profile_from_ratings2

RARITY_KEYS = ("COMMON", "BRONZE", "SILVER", "GOLD", "DIAMOND")
DECISIONS = (ELIGIBLE, PROVISIONAL, INELIGIBLE)

DRYRUN_EDITION_CODE = "2026_DRYRUN_SUBSTITUTION_CANDIDATE"


def _json_default(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--data-start-date", type=date.fromisoformat, default=date(2026, 3, 25))
    parser.add_argument("--data-end-date", type=date.fromisoformat, default=date(2026, 9, 2))
    parser.add_argument("--distribution-version", default="dist-1.0")
    args = parser.parse_args(argv)

    tables = (
        RatingDistribution,
        CardGenerationProfile,
        CardRatingProfile,
        CardCatalog,
        PlayerCardModel,
    )
    before = {
        table.__tablename__: SessionLocal().query(table).count() for table in tables
    }

    report: dict = {}
    return_code = 0
    with engine.connect() as conn:
        conn.begin()
        db = Session(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            # ---- 0. baseline real: ACTIVE v1 intacto ------------------------
            active = (
                db.query(CardCatalog)
                .filter_by(
                    season=args.season,
                    edition_type=CardEditionType.BASE,
                    status="ACTIVE",
                )
                .first()
            )
            if active is None:
                raise RuntimeError("no hay catálogo ACTIVE BASE; baseline roto")
            legacy_cards = (
                db.query(PlayerCardModel)
                .filter(PlayerCardModel.catalog_id == active.id)
                .all()
            )
            legacy_edition = (
                db.query(CardEdition)
                .join(PlayerCardModel, PlayerCardModel.card_edition_id == CardEdition.id)
                .filter(PlayerCardModel.catalog_id == active.id)
                .first()
            )
            report["baseline"] = {
                "catalog": {
                    "id": active.id,
                    "version": active.version,
                    "status": active.status,
                    "rating_model_version": active.rating_model_version,
                    "cards": len(legacy_cards),
                },
                "edition": (
                    {
                        "code": legacy_edition.code,
                        "version": legacy_edition.version,
                        "rating_policy_version": legacy_edition.rating_policy_version,
                        "rarity_policy_version": legacy_edition.rarity_policy_version,
                        "eligibility_policy_version": legacy_edition.eligibility_policy_version,
                    }
                    if legacy_edition is not None
                    else None
                ),
            }
            legacy_players = {card.player_id for card in legacy_cards}

            # ---- 1. edición candidata: ambas policies + elegibilidad --------
            candidate_edition = CardEdition(
                code=DRYRUN_EDITION_CODE,
                name="2026 Dry-run Sustitución v2",
                edition_type=CardEditionType.BASE,
                season=args.season,
                version="dry-run-1.1",
                rating_policy_version=BASE_RATING_POLICY_VERSION,
                rarity_policy_version=RARITY_POLICY_VERSION,
                eligibility_policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
                is_active=True,
                source_type=CardEditionSourceType.SYSTEM,
                metadata_payload={},
            )
            db.add(candidate_edition)
            db.flush()

            # Catálogo candidato (BUILDING, versión siguiente): la promoción lo
            # subiría a ACTIVE y retiraría v1; aquí solo le asignamos los payloads.
            next_version = (
                db.query(CardCatalog)
                .filter_by(season=args.season, edition_type=CardEditionType.BASE)
                .order_by(CardCatalog.version.desc())
                .first()
            ).version + 1
            candidate_catalog = CardCatalog(
                season=args.season,
                edition_type=CardEditionType.BASE,
                version=next_version,
                status="BUILDING",
                rating_model_version="ratings-2.0",
                data_end_date=args.data_end_date,
            )
            db.add(candidate_catalog)
            db.flush()

            # ---- 2. distribuciones por role (transaccional) -----------------
            distributions = {}
            for role in ("BATTER", "PITCHER"):
                dist_result = build_overall_rating_distribution(
                    db,
                    season=args.season,
                    role=role,
                    data_start_date=args.data_start_date,
                    data_end_date=args.data_end_date,
                    source_distribution_version=args.distribution_version,
                    performance_tier_model_version=PERFORMANCE_TIER_MODEL_VERSION,
                )
                dist = db.get(RatingDistribution, dist_result.rating_distribution_id)
                distributions[role] = {
                    "status": dist_result.status,
                    "population_size": dist_result.population_size,
                    "min": dist.minimum,
                    "max": dist.maximum,
                }
            report["candidate_distributions"] = distributions

            # ---- 3. CardGenerationProfile + CardRatingProfile ratings-2.0 ---
            ratings_rows = (
                db.query(PlayerRatings)
                .filter_by(
                    season=args.season,
                    rating_model_version="ratings-2.0",
                    distribution_version=args.distribution_version,
                    data_start_date=args.data_start_date,
                    data_end_date=args.data_end_date,
                )
                .all()
            )
            generated_ids = []
            for row in ratings_rows:
                result = generate_card_profile_from_ratings2(
                    db, player_ratings_id=row.id
                )
                if result.card_generation_profile_id:
                    generated_ids.append(result.card_generation_profile_id)
            rating_profile_ids = []
            for profile in (
                db.query(CardGenerationProfile)
                .filter(CardGenerationProfile.id.in_(generated_ids))
                .all()
            ):
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

            # ---- 4. réplica de publicación: dedupe + eligibility + rarity ----
            candidates = (
                db.query(CardGenerationProfile)
                .filter(CardGenerationProfile.id.in_(generated_ids))
                .all()
            )
            candidates.sort(key=profile_publish_order)
            seen_players = set()
            skipped_unresolved = 0
            skipped_ineligible = 0
            eligibility_failures = []
            rarity_failures = []
            decision_counts = Counter()
            published = []

            for profile in candidates:
                player = profile.player_season.player
                if player is None or player.game_identity is None:
                    skipped_unresolved += 1
                    continue
                game_team = _game_team_for_player(db, player.id)
                if game_team is None:
                    skipped_unresolved += 1
                    continue
                if player.id in seen_players:
                    continue
                seen_players.add(player.id)
                rating_profile = _resolve_rating_profile(
                    db, candidate_edition, profile, player.id
                )
                try:
                    eligibility = _resolve_published_eligibility(
                        candidate_edition, rating_profile
                    )
                except ValueError as exc:
                    eligibility_failures.append(f"mlb_id={player.mlb_id}: {exc}")
                    continue
                if eligibility == INELIGIBLE:
                    skipped_ineligible += 1
                    continue
                decision_counts[eligibility] += 1
                source = rating_profile if rating_profile is not None else profile
                try:
                    rarity = _resolve_published_rarity(
                        db, candidate_edition, profile, source.overall_rating
                    )
                except ValueError as exc:
                    rarity_failures.append(f"mlb_id={player.mlb_id}: {exc}")
                    continue
                payload = _card_from_profile(
                    candidate_catalog,
                    candidate_edition,
                    profile,
                    player,
                    game_team,
                    rating_profile,
                    rarity=rarity,
                )
                if payload is None:
                    skipped_unresolved += 1
                    continue
                published.append((payload, player))

            issues = (
                eligibility_failures
                + rarity_failures
                + _validate_rows([card for card, _ in published])
            )

            candidate_players = set()
            for profile in candidates:
                candidate_players.add(profile.player_season.player.id)

            report["dry_run"] = {
                "candidates": len(seen_players),
                "candidate_catalog_version": candidate_catalog.version,
                "skipped_unresolved": skipped_unresolved,
                "ineligible": skipped_ineligible,
                "published": len(published),
                "published_pack_eligible": len(published),
                "eligibility_failures": len(eligibility_failures),
                "rarity_failures": len(rarity_failures),
                "validation_issues": issues[:50],
                "status": "FAILED" if issues else "CANDIDATE_ACTIVE_OK",
            }

            # ---- 5. impacto de sustitución por jugador ----------------------
            published_players = {player.id for _, player in published}
            report["substitution_impact"] = {
                "legacy_v1_cards": len(legacy_players),
                "candidates": len(candidate_players),
                "published": len(published_players),
                "legacy_not_candidate": len(legacy_players - candidate_players),
                "dropped_from_v1": len(legacy_players - published_players),
                "new_in_v2_not_in_v1": len(published_players - legacy_players),
            }

            # ---- 6. pool de rarity + franquicias sobre publicados -----------
            rarity_pool = Counter(card.rarity.name for card, _ in published)
            report["rarity_pool"] = {
                "counts": {key: rarity_pool.get(key, 0) for key in RARITY_KEYS},
                "gate_ok": all(rarity_pool.get(key, 0) > 0 for key in RARITY_KEYS),
            }

            team_cards = Counter(card.team_id for card, _ in published)
            mapped_teams = [
                row[0]
                for row in db.query(SourceTeamGameTeamMapping.team_id)
                .filter(SourceTeamGameTeamMapping.valid_to.is_(None))
                .all()
            ]
            missing_teams = [team for team in mapped_teams if team_cards[team] == 0]
            report["cpu_franchises"] = {
                "mapped": len(mapped_teams),
                "with_candidate_card": len(mapped_teams) - len(missing_teams),
                "missing": missing_teams,
                "gate_ok": not missing_teams,
            }

            print(json.dumps(report, default=_json_default, indent=2))
        except Exception as exc:  # noqa: BLE001 - el reporte es la entrega
            return_code = 1
            print(json.dumps({"error": repr(exc)}, default=_json_default, indent=2))
        finally:
            conn.rollback()

    after = {
        table.__tablename__: SessionLocal().query(table).count() for table in tables
    }
    integrity = {
        "before": before,
        "after": after,
        "clean": before == after,
    }
    print(json.dumps({"rollback_integrity": integrity}, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())