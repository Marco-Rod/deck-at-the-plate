"""Fase B (dry-run): publicación transaccional ratings-2.0 + rarity-policy-2.0.

Reproduce la Fase A contrato-edición de principio a fin SIN persistir nada:

    1. Construye RatingDistribution por role (transaccional).
    2. Genera los CardGenerationProfile ratings-2.0 (transaccional).
    3. Genera los CardRatingProfile BASE (identity) (transaccional).
    4. Replica EXACTA el loop de publish_card_catalog sobre una edición
       transaccional que declara both policies, y mide:
         - cards total, rarity counts/%, rarity por role/team
         - OVR min/avg/max por rarity
         - gén-tier vs final-tier vs collectible rarity (gate de equivalencia)
         - population/role/distribution de cada tier

Seguridad: en lugar de SessionLocal (cuyos commit() internos persistirian),
la session se une a una conexión con join_transaction_mode="create_savepoint":
cada commit interno es scope de savepoint dentro de la transacción de la
Connection; el ROLLBACK final descarta TODO. El catálogo real queda intacto.
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from statistics import fmean

from sqlalchemy.orm import Session

from app.database import engine, SessionLocal
from app.models import (
    CardCatalog,
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    CardGenerationProfile,
    PlayerRatings,
    RatingDistribution,
)
from etl.config.performance_tier_2 import PERFORMANCE_TIER_MODEL_VERSION
from etl.services.card_catalog import (
    _card_from_profile,
    _game_team_for_player,
    _resolve_published_rarity,
    _resolve_rating_profile,
    _validate_rows,
    profile_publish_order,
)
from etl.services.card_rating_policies import BASE_RATING_POLICY_VERSION
from etl.services.card_rating_profiles import generate_card_rating_profile
from etl.services.rarity_policies import final_performance_tier
from etl.services.rating_distributions import build_overall_rating_distribution
from etl.services.ratings2_card_profiles import generate_card_profile_from_ratings2

RARITY_KEYS = ("COMMON", "BRONZE", "SILVER", "GOLD", "DIAMOND")


def _json_default(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _round(value: float) -> float:
    return round(value, 2)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--data-start-date", type=date.fromisoformat, default=date(2026, 3, 25))
    parser.add_argument("--data-end-date", type=date.fromisoformat, default=date(2026, 9, 2))
    parser.add_argument("--distribution-version", default="dist-1.0")
    args = parser.parse_args(argv)

    with engine.connect() as conn:
        conn.begin()
        db = Session(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        before = SessionLocal().query(RatingDistribution).count()
        report: dict = {}
        return_code = 0
        try:
            # ---- 1. edición transaccional que declara ambas políticas -------
            edition = CardEdition(
                code="2026_DRYRUN_RARITY_POLICY",
                name="2026 Dry-run Rarity Policy",
                edition_type=CardEditionType.BASE,
                season=args.season,
                version="dry-run-1.0",
                rating_policy_version=BASE_RATING_POLICY_VERSION,
                rarity_policy_version="rarity-policy-2.0",
                is_active=True,
                source_type=CardEditionSourceType.SYSTEM,
                metadata_payload={},
            )
            db.add(edition)
            db.flush()

            # ---- 2. distribuciones por role ---------------------------------
            dist_report = {}
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
                rating_distribution = db.get(
                    RatingDistribution, dist_result.rating_distribution_id
                )
                dist_report[role] = {
                    "status": dist_result.status,
                    "rating_distribution_id": dist_result.rating_distribution_id,
                    "population_size": dist_result.population_size,
                    "min": rating_distribution.minimum,
                    "max": rating_distribution.maximum,
                    "mean": rating_distribution.population_mean,
                }
            report["distributions"] = dist_report

            # ---- 3. CardGenerationProfile ratings-2.0 ------------------------
            generation_results = Counter()
            generated_ids = []
            ratings = (
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
            for row in ratings:
                result = generate_card_profile_from_ratings2(db, player_ratings_id=row.id)
                generation_results[result.status] += 1
                if result.card_generation_profile_id:
                    generated_ids.append(result.card_generation_profile_id)
            report["generation_profiles"] = dict(generation_results)

            # ---- 4. CardRatingProfile BASE (identity) -----------------------
            rating_profile_results = Counter()
            profiles = (
                db.query(CardGenerationProfile)
                .filter(CardGenerationProfile.id.in_(generated_ids))
                .all()
            )
            for profile in profiles:
                result = generate_card_rating_profile(
                    db,
                    source_player_ratings_id=profile.player_ratings_id,
                    card_edition_id=edition.id,
                )
                rating_profile_results[result.status] += 1
            report["card_rating_profiles"] = dict(rating_profile_results)

            # ---- 5. réplica exacta del loop de publicación -------------------
            active_catalog = (
                db.query(CardCatalog)
                .filter_by(
                    season=args.season,
                    edition_type=CardEditionType.BASE,
                    status="ACTIVE",
                )
                .first()
            )
            candidates = (
                db.query(CardGenerationProfile)
                .filter(CardGenerationProfile.id.in_(generated_ids))
                .all()
            )
            # Misma regla que publish_card_catalog: orden determinista y
            # two-way = rol de la posición primaria (reproducibilidad del dry-run).
            candidates.sort(key=profile_publish_order)
            seen_players = set()
            skipped_unresolved = 0
            rarity_failures = []
            cards = []

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
                rating_profile = _resolve_rating_profile(db, edition, profile, player.id)
                source = rating_profile if rating_profile is not None else profile
                try:
                    rarity = _resolve_published_rarity(
                        db, edition, profile, source.overall_rating
                    )
                except ValueError as exc:
                    rarity_failures.append(f"mlb_id={player.mlb_id}: {exc}")
                    continue
                payload = _card_from_profile(
                    active_catalog,
                    edition,
                    profile,
                    player,
                    game_team,
                    rating_profile,
                    rarity=rarity,
                )
                if payload is None:
                    skipped_unresolved += 1
                    continue
                cards.append((payload, profile, rating_profile))

            issues = rarity_failures + _validate_rows([c for c, _, _ in cards])
            if issues:
                report["publish_replica"] = {"status": "FAILED", "issues": issues[:50]}
                print(json.dumps(report, default=_json_default, indent=2))
                return_code = 2
            else:
                report["publish_replica"] = {
                    "status": "ACTIVE",
                    "created": len(cards),
                    "skipped_unresolved": skipped_unresolved,
                    "rarity_failures": len(rarity_failures),
                }

                # ---- 6. métricas --------------------------------------------
                card_rows = []
                for card, profile, rating_profile in cards:
                    metadata = profile.calculation_metadata or {}
                    distribution = db.get(
                        RatingDistribution, metadata.get("rating_distribution_id")
                    )
                    final_tier = final_performance_tier(
                        card.overall, distribution
                    ).performance_tier.name
                    card_rows.append(
                        {
                            "card": card,
                            "role": profile.role,
                            "team_id": card.team_id,
                            "overall": card.overall,
                            "rarity": card.rarity.name,
                            # OVR heredado por el perfil desde el PlayerRatings
                            # de ratings-2.0 (columna del CardGenerationProfile).
                            "generation_overall": profile.overall_rating,
                            "source_overall": profile.player_ratings.overall_rating,
                            "generation_tier": metadata.get("performance_tier"),
                            "final_tier": final_tier,
                            "mlb_id": profile.player_season.player.mlb_id,
                            "rating_distribution_id": metadata.get(
                                "rating_distribution_id"
                            ),
                            "population_size": distribution.population_size,
                        }
                    )

                rarity_counts = Counter(row["rarity"] for row in card_rows)
                overall_by_rarity = {}
                for rarity_key in RARITY_KEYS:
                    values = [row["overall"] for row in card_rows if row["rarity"] == rarity_key]
                    overall_by_rarity[rarity_key] = (
                        {
                            "count": len(values),
                            "min": min(values),
                            "avg": _round(fmean(values)),
                            "max": max(values),
                        }
                        if values
                        else {"count": 0, "min": None, "avg": None, "max": None}
                    )
                rarity_by_role = {
                    role: {
                        rarity_key: sum(
                            1
                            for r in card_rows
                            if r["role"] == role and r["rarity"] == rarity_key
                        )
                        for rarity_key in RARITY_KEYS
                    }
                    for role in ("BATTER", "PITCHER")
                }
                rarity_by_team = defaultdict(Counter)
                for row in card_rows:
                    rarity_by_team[row["team_id"]][row["rarity"]] += 1

                generation_vs_final_diffs = [
                    row
                    for row in card_rows
                    if row["generation_tier"] != row["final_tier"]
                ]
                overall_diffs = [
                    row
                    for row in card_rows
                    if row["generation_overall"] != row["overall"]
                ]

                report["totals"] = {"cards": len(card_rows)}
                report["rarity_counts"] = dict(rarity_counts)
                report["rarity_pct"] = {
                    rarity_key: _round(100 * rarity_counts[rarity_key] / len(card_rows))
                    for rarity_key in RARITY_KEYS
                }
                report["overall_by_rarity"] = overall_by_rarity
                report["rarity_by_role"] = rarity_by_role
                report["rarity_by_team"] = {
                    team: dict(counts) for team, counts in sorted(rarity_by_team.items())
                }
                report["tier_counts"] = {
                    "generation_tier": dict(sorted(dict(Counter(r["generation_tier"] for r in card_rows)).items())),
                    "final_tier": dict(sorted(dict(Counter(r["final_tier"] for r in card_rows)).items())),
                    "collectible_rarity": dict(sorted(rarity_counts.items())),
                }
                report["tier_changes_generation_vs_final"] = {
                    "count": len(generation_vs_final_diffs),
                    "sample": [
                        {
                            "mlb_id": r["mlb_id"],
                            "role": r["role"],
                            "overall": r["overall"],
                            "generation_tier": r["generation_tier"],
                            "final_tier": r["final_tier"],
                        }
                        for r in generation_vs_final_diffs[:10]
                    ],
                }
                report["overall_equivalence_generation_vs_final"] = {
                    "count_diffs": len(overall_diffs),
                    "sample": [
                        {
                            "mlb_id": r["mlb_id"],
                            "role": r["role"],
                            "generation_overall": r["generation_overall"],
                            "final_overall": r["overall"],
                        }
                        for r in overall_diffs[:10]
                    ],
                }
                source_vs_final_diffs = [
                    r for r in card_rows if r["source_overall"] != r["overall"]
                ]
                report["overall_equivalence_source_vs_final"] = {
                    "count_diffs": len(source_vs_final_diffs),
                    "sample": [
                        {
                            "mlb_id": r["mlb_id"],
                            "role": r["role"],
                            "source_overall": r["source_overall"],
                            "final_overall": r["overall"],
                        }
                        for r in source_vs_final_diffs[:10]
                    ],
                }
                report["equivalence_gate"] = {
                    "generation_overall_eq_final_overall": len(overall_diffs) == 0,
                    "generation_tier_eq_final_tier": len(generation_vs_final_diffs) == 0,
                }
                report["distribution_populations"] = {
                    role: {
                        "population_size": dist_report[role]["population_size"],
                        "min": dist_report[role]["min"],
                        "max": dist_report[role]["max"],
                        "mean": dist_report[role]["mean"],
                    }
                    for role in ("BATTER", "PITCHER")
                }

                print(json.dumps(report, default=_json_default, indent=2))
                return_code = 0
        finally:
            conn.rollback()
            after = SessionLocal().query(RatingDistribution).count()
            db.close()
            print(
                "// rollback_integrity: "
                f"distributions_persisted={after} (antes={before})"
            )
        return return_code


if __name__ == "__main__":
    raise SystemExit(main())