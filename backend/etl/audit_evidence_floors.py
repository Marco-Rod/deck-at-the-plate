"""Dry-run de minimum publication evidence floors (base-eligibility-1.1 gate).

NO cambia ninguna policy. Grid FINAL independiente POR ATRIBUTO sobre las 829
cartas post profile_publish_order:

    contact : .20 .25 .30
    vision  : .20 .25 .30
    velocity: .15 .20 .25 .30
    movement: .15 .20 .25 .30

Matriz cartesiana (4x4x...): cada combinacion de floors independientes se
evalua junto (el atributo calibrado mas debil decide). Por combinacion se
reporta total/BATTER/PITCHER, rarity, team, drivers y cards con >1 fallo.

Por atributo (independiente de la combinacion) se reporta por floor:
    - below_floor / missing_evidence
    - metricas humanas del subconjunto debajo del floor
      (BATTER: pa; PITCHER velocity: batters_faced + pitches;
       movement: evaluable_pitches) con median/p90

Inspeccion individual del candidato all-0.25: cada INELIGIBLE con player, rol,
posicion primaria, evidencia por atributo, muestra humana y que atributo
dispara el fallo — para confirmar que el floor captura participaciones
marginales, no agujeros de ingestion. La DB queda intacta (savepoint+rollback,
integridad por conteos).
"""

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from itertools import product

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

FLOOR_GRID = {
    "contact": (Decimal("0.20"), Decimal("0.25"), Decimal("0.30")),
    "vision": (Decimal("0.20"), Decimal("0.25"), Decimal("0.30")),
    "velocity": (Decimal("0.15"), Decimal("0.20"), Decimal("0.25"), Decimal("0.30")),
    "movement": (Decimal("0.15"), Decimal("0.20"), Decimal("0.25"), Decimal("0.30")),
}
CALIBRATED_ORDER = tuple(FLOOR_GRID)

CANDIDATE_FLOORS = {
    "contact": Decimal("0.25"),
    "vision": Decimal("0.25"),
    "velocity": Decimal("0.25"),
    "movement": Decimal("0.25"),
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
    sorted_values = sorted(values)
    if not sorted_values:
        return {"n": 0, "median": None, "p90": None}
    return {
        "n": len(sorted_values),
        "median": _nearest_rank(sorted_values, 0.50),
        "p90": _nearest_rank(sorted_values, 0.90),
    }


def _combo_key(combo) -> str:
    return "|".join(f"{attr}={combo[attr]}" for attr in CALIBRATED_ORDER)


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
                code="2026_DRYRUN_FLOOR_GRID",
                name="2026 Dry-run Floor Grid",
                edition_type=CardEditionType.BASE,
                season=args.season,
                version="dry-run-1.1-grid",
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
                "candidate_combo": _combo_key(CANDIDATE_FLOORS),
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

            # ---- 5. policy vigente de referencia -----------------------------
            current_policy = Counter(c["assessment"].decision for c in cards)
            report["reference_policy"] = {
                "INELIGIBLE": current_policy.get(INELIGIBLE, 0),
                "PROVISIONAL": current_policy.get(PROVISIONAL, 0),
                "ELIGIBLE": current_policy.get(ELIGIBLE, 0),
            }

            # ---- 6. per-atributo: counts y muestras por floor -----------------
            per_attribute = {}
            for attribute, floors in FLOOR_GRID.items():
                role = "BATTER" if attribute in CALIBRATED_ATTRS["BATTER"] else "PITCHER"
                role_cards = [c for c in cards if c["role"] == role]
                per_attribute[attribute] = {}
                for floor in floors:
                    below_floor = []
                    missing = 0
                    for c in role_cards:
                        evidence = c["assessment"].evidence.attributes[attribute].evidence
                        if evidence is None:
                            missing += 1
                        elif evidence < floor:
                            below_floor.append(c)
                    per_attribute[attribute][str(floor)] = {
                        "below_floor": len(below_floor),
                        "missing_evidence": missing,
                        "sample_metric": _sample_metric(
                            role, attribute, below_floor,
                            batter_pa, pitcher_counts, evaluable_counts,
                        ),
                    }
            report["per_attribute_floors"] = per_attribute

            # ---- 7. matriz cartesiana de floors independientes ----------------
            def decide_under(combo, card) -> str:
                for attribute in CALIBRATED_ATTRS[card["role"]]:
                    evidence = card["assessment"].evidence.attributes[attribute].evidence
                    if evidence is None or evidence < combo[attribute]:
                        return INELIGIBLE
                return PROVISIONAL

            matrix = []
            for floors_tuple in product(*(FLOOR_GRID[a] for a in CALIBRATED_ORDER)):
                combo = dict(zip(CALIBRATED_ORDER, floors_tuple))
                ineligible = []
                for card in cards:
                    if decide_under(combo, card) == INELIGIBLE:
                        ineligible.append(card)
                if not ineligible:
                    matrix.append({
                        "combo": _combo_key(combo),
                        "INELIGIBLE": 0,
                        "BATTER": 0,
                        "PITCHER": 0,
                    })
                    continue
                bat = Counter(card["role"] for card in ineligible)
                rarity = Counter(card["rarity"] for card in ineligible)
                team = Counter(card["team_id"] for card in ineligible)
                drivers = defaultdict(int)
                multi_fail = 0
                for card in ineligible:
                    failing = [
                        a for a in CALIBRATED_ATTRS[card["role"]]
                        if (card["assessment"].evidence.attributes[a].evidence or Decimal("0")) < combo[a]
                    ]
                    for a in failing:
                        drivers[a] += 1
                    if len(failing) > 1:
                        multi_fail += 1
                matrix.append({
                    "combo": _combo_key(combo),
                    "INELIGIBLE": len(ineligible),
                    "BATTER": bat.get("BATTER", 0),
                    "PITCHER": bat.get("PITCHER", 0),
                    "by_rarity": {k: rarity.get(k, 0) for k in RARITY_KEYS},
                    "by_team": {
                        "min": min(team.values()),
                        "max": max(team.values()),
                        "avg": round(sum(team.values()) / len(team), 2),
                    },
                    "drivers": {k: drivers[k] for k in CALIBRATED_ORDER},
                    "cards_with_multi_fail": multi_fail,
                })
            report["matrix"] = matrix

            # ---- 8. inspeccion individual del candidato all-0.25 --------------
            inspection = []
            for card in cards:
                if decide_under(CANDIDATE_FLOORS, card) != INELIGIBLE:
                    continue
                player = card["profile"].player_season.player
                failing = [
                    a for a in CALIBRATED_ATTRS[card["role"]]
                    if (card["assessment"].evidence.attributes[a].evidence or Decimal("0")) < CANDIDATE_FLOORS[a]
                ]
                inspection.append({
                    "name": player.full_name,
                    "mlb_id": player.mlb_id,
                    "role": card["role"],
                    "primary_position": player.primary_position,
                    "rarity": card["rarity"],
                    "team_id": card["team_id"],
                    "evidence": {
                        a: str(card["assessment"].evidence.attributes[a].evidence)
                        for a in CALIBRATED_ATTRS[card["role"]]
                    },
                    "sample": _card_sample(card, batter_pa, pitcher_counts, evaluable_counts),
                    "drivers": failing,
                })
            inspection.sort(key=lambda row: row["role"])
            report["candidate_inspection"] = {
                "combo": _combo_key(CANDIDATE_FLOORS),
                "total": len(inspection),
                "cards": inspection,
            }

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


def _metric_values(role, attribute, below_cards, batter_pa, pitcher_counts, evaluable_counts):
    if role == "BATTER":
        return [("pa", batter_pa.get(c["profile"].player_season_id, 0)) for c in below_cards]
    if attribute == "velocity":
        rows = []
        for c in below_cards:
            bf, pitches = pitcher_counts.get(c["profile"].player_season_id, (0, 0))
            rows.append(("batters_faced", bf))
            rows.append(("pitches", pitches))
        return rows
    return [
        ("evaluable_pitches", evaluable_counts.get(c["profile"].player_season_id, 0))
        for c in below_cards
    ]


def _sample_metric(role, attribute, below_cards, batter_pa, pitcher_counts, evaluable_counts) -> dict:
    if not below_cards:
        return {"n": 0}
    rows = _metric_values(role, attribute, below_cards, batter_pa, pitcher_counts, evaluable_counts)
    by_metric = {}
    for metric in {m for m, _ in rows}:
        by_metric[metric] = _summary([value for m, value in rows if m == metric])
    return by_metric


def _card_sample(card, batter_pa, pitcher_counts, evaluable_counts) -> dict:
    ps_id = card["profile"].player_season_id
    if card["role"] == "BATTER":
        return {"pa": batter_pa.get(ps_id, 0)}
    bf, pitches = pitcher_counts.get(ps_id, (0, 0))
    return {
        "batters_faced": bf,
        "pitches": pitches,
        "evaluable_pitches": evaluable_counts.get(ps_id, 0),
    }


if __name__ == "__main__":
    raise SystemExit(main())