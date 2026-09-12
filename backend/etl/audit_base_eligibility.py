"""Eligibility BASE (dry-run v2): población post-dedupe + bandas de evidencia.

NO activa nada. Sobre la población REAL ratings-2.0 midamos la frontera de
base-eligibility-1.0 en DOS vistas (el catalogo publica cartas, no filas):

    vista A (before dedupe): 869 rating rows — cada rol del two-way cuenta.
    vista B (after dedupe) : 829 cartas — replica profile_publish_order
                             (mana el rol de la posicion primaria); la carta
                             hereda la decision de evidencia de SU rol ganador.

Entregables:
    - buckets por role/total en ambas vistas
    - matriz two-way: decision del rol publicado vs rol descartado
    - drivers de INELIGIBLE por atributo calibrado (vista cartas)
    - bandas de evidencia por atributo calibrado, ancladas a su umbral
      (responde: los INELIGIBLE son evidencia muy baja o apenas la frontera?)
    - cross buckets x rarity y team_impact sobre la vista cartas

Seguridad: Connection.begin() + Session(create_savepoint); las distribuciones
y los CardGenerationProfile ratings-2.0 se generan dentro (igual que
audit_rarity_policy_2) y el ROLLBACK final los descarta. Integridad por
conteos antes/despues de RatingDistribution y CardGenerationProfile.
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import engine, SessionLocal
from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    CardGenerationProfile,
    PlayerRatings,
    RatingDistribution,
)
from etl.config.performance_tier_2 import PERFORMANCE_TIER_MODEL_VERSION
from etl.services.base_eligibility_policy import (
    ELIGIBLE,
    INELIGIBLE,
    PROVISIONAL,
    assess_base_eligibility,
)
from etl.services.base_evidence_policy import CALIBRATED_THRESHOLDS
from etl.services.card_catalog import _game_team_for_player, profile_publish_order
from etl.services.rarity_policies import (
    RARITY_POLICY_VERSION,
    final_performance_tier,
    resolve_card_rarity,
)
from etl.services.rating_distributions import build_overall_rating_distribution
from etl.services.ratings2_card_profiles import generate_card_profile_from_ratings2

RARITY_KEYS = ("COMMON", "BRONZE", "SILVER", "GOLD", "DIAMOND")
DECISIONS = (ELIGIBLE, PROVISIONAL, INELIGIBLE)
ROLES = ("BATTER", "PITCHER")

# Edges fijos de banda; el umbral propio del atributo se inserta en los edges,
# de modo que para T=0.90 salen exactamente <.25/.25-.49/.50-.69/.70-.79/
# .80-.89/>=.90, y para T mas bajo la banda pegada a la frontera se compacta.
_BAND_EDGES = (Decimal("0.25"), Decimal("0.50"), Decimal("0.70"),
               Decimal("0.80"), Decimal("0.90"))


def _json_default(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _evidence_bands(values, threshold) -> dict:
    """Histograma por bandas ancladas al umbral; values Decimal o None."""
    population = [v for v in values if v is not None]
    bands = []
    if population:
        edges = sorted({Decimal("0.00")} | set(_BAND_EDGES) | {threshold})
        for lo, hi in zip(edges, edges[1:]):
            bands.append({
                "band": f"{lo}-{hi}",
                "count": sum(1 for v in population if lo <= v < hi),
                "below_threshold": hi <= threshold,
            })
        last = edges[-1]
        bands.append({
            "band": f">={last}",
            "count": sum(1 for v in population if v >= last),
            "below_threshold": False,
        })
    return {
        "threshold": str(threshold),
        "bands": bands,
        "total_observed": len(population),
        "total_below_threshold": sum(1 for v in population if v < threshold),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--data-start-date", type=date.fromisoformat, default=date(2026, 3, 25))
    parser.add_argument("--data-end-date", type=date.fromisoformat, default=date(2026, 9, 2))
    parser.add_argument("--distribution-version", default="dist-1.0")
    parser.add_argument("--top-teams", type=int, default=15)
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
                code="2026_DRYRUN_ELIGIBILITY",
                name="2026 Dry-run Eligibility",
                edition_type=CardEditionType.BASE,
                season=args.season,
                version="dry-run-1.0",
                rarity_policy_version=RARITY_POLICY_VERSION,
                source_type=CardEditionSourceType.SYSTEM,
                metadata_payload={},
            )
            db.add(edition)
            db.flush()

            dist_by_role = {}
            report["distributions"] = {}
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
                report["distributions"][role] = {
                    "status": dist_result.status,
                    "population_size": dist_result.population_size,
                    "min": dist.minimum,
                    "max": dist.maximum,
                }

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

            # ---- 3. vista A (869 rows) y vista B (829 cartas) ----------------
            def evaluate(role: str, rating) -> dict:
                assessment = assess_base_eligibility(role=role, player_ratings=rating)
                tier = final_performance_tier(
                    rating.overall_rating, dist_by_role[role]
                )
                rarity = resolve_card_rarity(
                    edition,
                    final_overall=rating.overall_rating,
                    performance_tier=tier.performance_tier,
                )
                return {
                    "player_id": rating.player_id,
                    "role": role,
                    "decision": assessment.decision,
                    "assessment": assessment,
                    "rarity": rarity.name,
                    "team_id": _game_team_for_player(db, rating.player_id),
                }

            rating_rows = [evaluate(r.role, r) for r in ratings_rows]

            generation_profiles.sort(key=profile_publish_order)
            seen_players = set()
            card_rows = []
            for profile in generation_profiles:
                if profile.player_season.player_id in seen_players:
                    continue
                seen_players.add(profile.player_season.player_id)
                rating = profile.player_ratings
                card_rows.append(
                    {**evaluate(rating.role, rating), "profile": profile}
                )

            roles_per_player = defaultdict(set)
            for profile in generation_profiles:
                roles_per_player[profile.player_season.player_id].add(profile.role)
            two_way_players = {
                p for p, roles in roles_per_player.items() if len(roles) == 2
            }

            report["population"] = {
                "rating_rows": len(rating_rows),
                "cards_after_dedupe": len(card_rows),
                "distinct_players": len(seen_players),
                "two_way_players": len(two_way_players),
            }

            # ---- 4. buckets en ambas vistas ----------------------------------
            def bucket_summary(rows):
                return {
                    "totals": dict(Counter(r["decision"] for r in rows)),
                    "by_role": {
                        role: dict(Counter(r["decision"] for r in rows if r["role"] == role))
                        for role in ROLES
                    },
                }

            report["buckets"] = {
                "before_dedupe_869_rows": bucket_summary(rating_rows),
                "after_dedupe_829_cards": bucket_summary(card_rows),
            }

            # matriz two-way: decision del rol publicado vs rol descartado
            by_player_role = defaultdict(dict)
            for r in rating_rows:
                by_player_role[r["player_id"]][r["role"]] = r["decision"]
            card_by_player = {r["player_id"]: r for r in card_rows}
            two_way_matrix = Counter()
            for player_id in two_way_players:
                card = card_by_player[player_id]
                card_role = card["profile"].role
                dropped_role = "PITCHER" if card_role == "BATTER" else "BATTER"
                dropped_decision = by_player_role[player_id].get(dropped_role)
                two_way_matrix[
                    (card_role, card["decision"], dropped_role, dropped_decision)
                ] += 1
            report["two_way_matrix"] = {
                f"{won_role}|{card_decision} (dropped {dropped_role}:{dropped_decision})": count
                for (won_role, card_decision, dropped_role, dropped_decision), count
                in sorted(two_way_matrix.items())
            }

            # ---- 5. drivers y status sobre la vista cartas -------------------
            ineligible_drivers = defaultdict(Counter)
            for r in card_rows:
                if r["decision"] != INELIGIBLE:
                    continue
                for attribute, assessment in r["assessment"].evidence.attributes.items():
                    if assessment.status == "BELOW_THRESHOLD":
                        ineligible_drivers[r["role"]][attribute] += 1
            report["ineligible_drivers_829_cards"] = {
                role: dict(counter) for role, counter in ineligible_drivers.items()
            }

            attribute_status = defaultdict(Counter)
            for r in card_rows:
                for attribute, assessment in r["assessment"].evidence.attributes.items():
                    attribute_status[attribute][assessment.status] += 1
            report["attribute_status_829_cards"] = {
                attribute: dict(counter) for attribute, counter in attribute_status.items()
            }

            # ---- 6. bandas de evidencia por atributo calibrado ---------------
            # sobre la vista cartas (829): BASE publica cartas, no role-rows.
            evidence_bands = {}
            for role in ROLES:
                role_evidence = defaultdict(list)
                for r in card_rows:
                    if r["role"] != role:
                        continue
                    for attribute, assessment in r["assessment"].evidence.attributes.items():
                        if assessment.evidence is not None:
                            role_evidence[attribute].append(assessment.evidence)
                role_bands = {}
                for attribute, values in role_evidence.items():
                    if attribute not in CALIBRATED_THRESHOLDS:
                        continue
                    role_bands[attribute] = _evidence_bands(
                        values, CALIBRATED_THRESHOLDS[attribute]
                    )
                evidence_bands[role] = role_bands
            report["evidence_bands"] = evidence_bands

            # ---- 7. rarity y team sobre la vista cartas ----------------------
            report["bucket_x_rarity_829_cards"] = {
                role: {
                    decision: {
                        rarity_key: sum(
                            1
                            for r in card_rows
                            if r["role"] == role
                            and r["decision"] == decision
                            and r["rarity"] == rarity_key
                        )
                        for rarity_key in RARITY_KEYS
                    }
                    for decision in DECISIONS
                }
                for role in ROLES
            }

            team_impact = defaultdict(Counter)
            for r in card_rows:
                team_impact[r["team_id"] or "sin_team"][r["decision"]] += 1
            team_summary = []
            for team_id, decisions in team_impact.items():
                team_summary.append(
                    {"team_id": team_id, "total": sum(decisions.values()),
                     "decisions": dict(decisions)}
                )
            team_summary.sort(
                key=lambda t: (-t["decisions"].get(INELIGIBLE, 0), -t["total"])
            )
            report["team_impact_top_829_cards"] = team_summary[: args.top_teams]

            print(json.dumps(report, default=_json_default, indent=2))
        except Exception as exc:  # noqa: BLE001 - el reporte es la entrega
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


if __name__ == "__main__":
    raise SystemExit(main())