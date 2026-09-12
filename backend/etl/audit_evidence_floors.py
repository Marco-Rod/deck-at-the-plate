"""Dry-run de minimum publication evidence floors (base-eligibility-1.1 candidate).

NO cambia ninguna policy. Mide sobre la población REAL ratings-2.0 dedupeada
(829 cartas, replica profile_publish_order como audit_base_eligibility) cómo
quedaría la frontera si eligibility distinguiera:

    evidence <  floor              -> INELIGIBLE  (muestra insuficiente)
    floor <= evidence < calibrated -> PROVISIONAL (evidencia sustancial)
    evidence >= calibrated         -> PASS        (umbral intacto base-evidence-1.0)

Por atributo calibrado se prueban floors candidatos separados:

    BATTER  contact/vision: 0.25 0.40 0.50 0.60
    PITCHER velocity/movement: 0.10 0.20 0.25 0.30

Por cada corte se reporta:
    - buckets por role/floor (corte conjunto: el atributo mas debil decide)
    - impacto por rarity y por team del corte conjunto
    - counts por atributo (debajo del floor, y evidence NULL)
    - metricas humanas de muestra del subconjunto debajo del floor
      (BATTER: pa median/p90; PITCHER velocity: batters_faced y pitches;
       movement: evaluable pitch count sobre PitcherPitchProfile)
        -> respuesta: la exclusion corresponde a temporada/base poco confiable
           o solo rebasa una frontera estadistica?

Seguridad: misma transaccion que audit_base_eligibility (savepoint + rollback);
integridad por conteos antes/despues de RatingDistribution y
CardGenerationProfile.
"""

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal
from app.models import (
    BatterSeasonStats,
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    CardGenerationProfile,
    PitcherPitchProfile,
    PitcherSeasonStats,
    PlayerRatings,
    RatingDistribution,
)
from etl.config.league_distributions import MOVEMENT_EXCLUDED_PITCH_TYPES
from etl.config.performance_tier_2 import PERFORMANCE_TIER_MODEL_VERSION
from etl.services.base_eligibility_policy import (
    ELIGIBLE,
    INELIGIBLE,
    PROVISIONAL,
    assess_base_eligibility,
)
from etl.services.base_evidence_policy import (
    CALIBRATED_THRESHOLDS,
    ROLE_ATTRIBUTES,
)
from etl.services.card_catalog import _game_team_for_player, profile_publish_order
from etl.services.rarity_policies import (
    RARITY_POLICY_VERSION,
    final_performance_tier,
    resolve_card_rarity,
)
from etl.services.rating_distributions import build_overall_rating_distribution
from etl.services.ratings2_card_profiles import generate_card_profile_from_ratings2

RARITY_KEYS = ("COMMON", "BRONZE", "SILVER", "GOLD", "DIAMOND")
ROLES = ("BATTER", "PITCHER")

CALIBRATED_ATTRS = {
    "BATTER": tuple(a for a in ROLE_ATTRIBUTES["BATTER"] if a in CALIBRATED_THRESHOLDS),
    "PITCHER": tuple(a for a in ROLE_ATTRIBUTES["PITCHER"] if a in CALIBRATED_THRESHOLDS),
}

FLOOR_CANDIDATES = {
    "BATTER": (
        Decimal("0.25"), Decimal("0.40"), Decimal("0.50"), Decimal("0.60"),
    ),
    "PITCHER": (
        Decimal("0.10"), Decimal("0.20"), Decimal("0.25"), Decimal("0.30"),
    ),
}


def _json_default(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _nearest_rank(sorted_values, quantile):
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1, int(math.ceil(quantile * len(sorted_values))) - 1)
    return sorted_values[index]


def _summary(values):
    """median/p90 por rango para el subconjunto debajo del floor."""
    sorted_values = sorted(values)
    if not sorted_values:
        return {"n": 0, "median": None, "p90": None}
    return {
        "n": len(sorted_values),
        "median": _nearest_rank(sorted_values, 0.50),
        "p90": _nearest_rank(sorted_values, 0.90),
    }


def _decide_under_floor(assessment, role, floor) -> str:
    """Corte conjunto: el atributo calibrado mas debil decide.

    evidence NULL o debajo del floor -> INELIGIBLE; si todos pasan el floor,
    quedan las senales de power/control/stuff que hoy son siempre PROVISIONAL.
    """
    for attribute in CALIBRATED_ATTRS[role]:
        evidence = assessment.evidence.attributes[attribute].evidence
        if evidence is None or evidence < floor:
            return INELIGIBLE
    return PROVISIONAL


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--data-start-date", type=date.fromisoformat, default=date(2026, 3, 25))
    parser.add_argument("--data-end-date", type=date.fromisoformat, default=date(2026, 9, 2))
    parser.add_argument("--distribution-version", default="dist-1.0")
    args = parser.parse_args(argv)

    before_distributions = SessionLocal().query(RatingDistribution).count()
    before_profiles = SessionLocal().query(CardGenerationProfile).count()
    report: dict = {}
    return_code = 0
    with engine.connect() as conn:
        conn.begin()
        db = Session(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            # ---- 1. distribuciones por role (transaccional, se descarta) ----
            edition = CardEdition(
                code="2026_DRYRUN_FLOORS",
                name="2026 Dry-run Evidence Floors",
                edition_type=CardEditionType.BASE,
                season=args.season,
                version="dry-run-1.1",
                rarity_policy_version=RARITY_POLICY_VERSION,
                source_type=CardEditionSourceType.SYSTEM,
                metadata_payload={},
            )
            db.add(edition)
            db.flush()

            dist_by_role = {}
            for role in ROLES:
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
                dist_by_role[role] = dist

            # ---- 2. generation profiles ratings-2.0 (transaccional) ----------
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
            generation_profiles = (
                db.query(CardGenerationProfile)
                .filter(CardGenerationProfile.id.in_(generated_ids))
                .all()
            )

            # ---- 3. poblacion post-dedupe (829 cartas) -----------------------
            generation_profiles.sort(key=profile_publish_order)
            seen_players = set()
            cards = []
            for profile in generation_profiles:
                if profile.player_season.player_id in seen_players:
                    continue
                seen_players.add(profile.player_season.player_id)
                rating = profile.player_ratings
                assessment = assess_base_eligibility(role=rating.role, player_ratings=rating)
                tier = final_performance_tier(rating.overall_rating, dist_by_role[rating.role])
                rarity = resolve_card_rarity(
                    edition,
                    final_overall=rating.overall_rating,
                    performance_tier=tier.performance_tier,
                )
                cards.append({
                    "profile": profile,
                    "role": rating.role,
                    "assessment": assessment,
                    "rarity": rarity.name,
                    "team_id": _game_team_for_player(db, profile.player_season.player_id) or "sin_team",
                })
            report["population"] = {
                "rating_rows": len(ratings_rows),
                "cards_after_dedupe": len(cards),
            }

            # ---- 4. metricas humanas de muestra por player_season ------------
            player_season_ids = [c["profile"].player_season_id for c in cards]
            batter_pa = dict(
                db.query(BatterSeasonStats.player_season_id, BatterSeasonStats.pa)
                .filter(BatterSeasonStats.player_season_id.in_(player_season_ids))
                .all()
            )
            pitcher_counts = {
                ps_id: (bf, pitches)
                for ps_id, bf, pitches in db.query(
                    PitcherSeasonStats.player_season_id,
                    PitcherSeasonStats.batters_faced,
                    PitcherSeasonStats.pitches,
                ).filter(PitcherSeasonStats.player_season_id.in_(player_season_ids)).all()
            }
            evaluable_counts = dict(
                db.query(
                    PitcherPitchProfile.player_season_id,
                    func.sum(PitcherPitchProfile.pitch_count),
                )
                .filter(
                    PitcherPitchProfile.player_season_id.in_(player_season_ids),
                    PitcherPitchProfile.batter_side == "ALL",
                    PitcherPitchProfile.pitch_count > 0,
                    PitcherPitchProfile.avg_pfx_x.isnot(None),
                    PitcherPitchProfile.avg_pfx_z.isnot(None),
                    ~PitcherPitchProfile.pitch_type.in_(MOVEMENT_EXCLUDED_PITCH_TYPES),
                )
                .group_by(PitcherPitchProfile.player_season_id)
                .all()
            )

            # ---- 5. v1 de referencia sobre las 829 cartas -------------------
            v1 = Counter(c["assessment"].decision for c in cards)
            report["reference_v1"] = {
                "INELIGIBLE": v1.get(INELIGIBLE, 0),
                "PROVISIONAL": v1.get(PROVISIONAL, 0),
                "ELIGIBLE": v1.get(ELIGIBLE, 0),
            }

            # ---- 6. cortes de floor -----------------------------------------
            floors_report = {}
            for role in ROLES:
                role_cards = [c for c in cards if c["role"] == role]
                role_floors = FLOOR_CANDIDATES[role]
                joint = {}
                per_attribute = {}
                for attribute in CALIBRATED_ATTRS[role]:
                    per_attribute[attribute] = {}
                    for floor in role_floors:
                        below = [
                            c for c in role_cards
                            if (c["assessment"].evidence.attributes[attribute].evidence or Decimal("0"))
                            < floor
                        ]
                        missing = [
                            c for c in role_cards
                            if c["assessment"].evidence.attributes[attribute].evidence is None
                        ]
                        per_attribute[attribute][str(floor)] = {
                            "below_floor": len(below),
                            "missing_evidence": len(missing),
                            "sample_metric": _sample_metric(db, role, attribute, below, batter_pa,
                                                            pitcher_counts, evaluable_counts),
                        }

                for floor in role_floors:
                    decided = Counter(_decide_under_floor(c["assessment"], role, floor) for c in role_cards)
                    ineligible = [c for c in role_cards if _decide_under_floor(c["assessment"], role, floor) == INELIGIBLE]
                    by_rarity = Counter(c["rarity"] for c in ineligible)
                    by_team = Counter(c["team_id"] for c in ineligible)
                    joint[str(floor)] = {
                        "n_cards": len(role_cards),
                        "INELIGIBLE": decided.get(INELIGIBLE, 0),
                        "PROVISIONAL": decided.get(PROVISIONAL, 0),
                        "pct_ineligible": round(decided.get(INELIGIBLE, 0) / len(role_cards), 3),
                        "by_rarity": {k: by_rarity.get(k, 0) for k in RARITY_KEYS},
                        "by_team": {
                            "min": min(by_team.values()) if by_team else 0,
                            "max": max(by_team.values()) if by_team else 0,
                            "avg": round(sum(by_team.values()) / len(by_team), 2) if by_team else 0.0,
                            "top": by_team.most_common(3),
                        },
                    }
                floors_report[role] = {"joint": joint, "per_attribute": per_attribute}
            report["floors"] = floors_report

            print(json.dumps(report, default=_json_default, indent=2))
        except Exception as exc:  # noqa: BLE001
            return_code = 1
            print(json.dumps({"error": repr(exc)}, default=_json_default, indent=2))
        finally:
            conn.rollback()

    after_distributions = SessionLocal().query(RatingDistribution).count()
    after_profiles = SessionLocal().query(CardGenerationProfile).count()
    integrity = {
        "rating_distributions": {"before": before_distributions, "after": after_distributions},
        "card_generation_profiles": {"before": before_profiles, "after": after_profiles},
        "clean": (
            before_distributions == after_distributions
            and before_profiles == after_profiles
        ),
    }
    print(json.dumps({"rollback_integrity": integrity}, indent=2))
    return return_code


def _sample_metric(db: Session, role, attribute, below, batter_pa, pitcher_counts, evaluable_counts) -> dict:
    """Metricas humanas del subconjunto debajo del floor."""
    if not below:
        return {"n": 0}
    players = []
    for card in below:
        ps_id = card["profile"].player_season_id
        if role == "BATTER":
            value = batter_pa.get(ps_id, 0)
            players.append({"metric": "pa", "value": value})
        elif attribute == "velocity":
            bf, pitches = pitcher_counts.get(ps_id, (0, 0))
            players.append({"metric": "batters_faced", "value": bf})
            players.append({"metric": "pitches", "value": pitches})
        else:  # movement
            players.append({"metric": "evaluable_pitches", "value": evaluable_counts.get(ps_id, 0)})
    by_metric = {}
    for metric in {p["metric"] for p in players}:
        values = sorted(p["value"] for p in players if p["metric"] == metric)
        by_metric[metric] = _summary(values)
    return by_metric


if __name__ == "__main__":
    raise SystemExit(main())