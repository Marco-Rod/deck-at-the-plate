"""Eligibility BASE (dry-run): mide antes de activar filtros.

NO activa nada: solo cuantifica cómo quedaría la frontera con
base-eligibility-1.0 sobre la población REAL ratings-2.0:

      PlayerRatings ratings-2.0
      + base-evidence-1.0
              ↓
      assess_base_eligibility -> ELIGIBLE / PROVISIONAL / INELIGIBLE
              ↓
      impacto por role / team / rarity

Entregables:
    - buckets por role y total, jugadores distintos
    - drivers de INELIGIBLE (atributo calibrado bajo el umbral)
    - tabla de status por atributo (qué está calibrado y qué no)
    - sensibilidad: % que caería bajo umbrales candidatos por atributo
    - cross buckets x rarity (por role)
    - impacto por franquicia pública

Seguridad: la sesión se une a una Connection con join_transaction_mode=
"create_savepoint" (igual que audit_rarity_policy_2). build_overall_rating_
distribution persiste dentro del savepoint; el ROLLBACK final descarta todo.
La evaluación de evidencia/eligibilidad es pura y no escribe nada. Integridad
verificada por conteos antes/después de RatingDistribution.
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
from etl.services.card_catalog import _game_team_for_player
from etl.services.rarity_policies import (
    RARITY_POLICY_VERSION,
    final_performance_tier,
    resolve_card_rarity,
)
from etl.services.rating_distributions import build_overall_rating_distribution

RARITY_KEYS = ("COMMON", "BRONZE", "SILVER", "GOLD", "DIAMOND")
DECISIONS = (ELIGIBLE, PROVISIONAL, INELIGIBLE)
DEFAULT_THRESHOLDS_CANDIDATES = (
    Decimal("0.30"), Decimal("0.40"), Decimal("0.50"),
    Decimal("0.60"), Decimal("0.70"), Decimal("0.80"),
)
ROLES = ("BATTER", "PITCHER")


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
    parser.add_argument("--top-teams", type=int, default=15)
    parser.add_argument(
        "--thresholds",
        nargs="*",
        type=Decimal,
        default=None,
        help="umbrales candidatos para la tabla de sensibilidad",
    )
    args = parser.parse_args(argv)
    thresholds = tuple(args.thresholds or DEFAULT_THRESHOLDS_CANDIDATES)

    before = SessionLocal().query(RatingDistribution).count()
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
            report["population"] = {
                "rows": len(ratings_rows),
                "batters": sum(1 for r in ratings_rows if r.role == "BATTER"),
                "pitchers": sum(1 for r in ratings_rows if r.role == "PITCHER"),
                "distinct_players": len({r.player_id for r in ratings_rows}),
            }

            # ---- 2. evidencia + eligibilidad + rarity + team por fila --------
            rows = []
            for rating in ratings_rows:
                assessment = assess_base_eligibility(
                    role=rating.role, player_ratings=rating
                )
                tier = final_performance_tier(rating.overall_rating, dist_by_role[rating.role])
                rarity = resolve_card_rarity(
                    edition,
                    final_overall=rating.overall_rating,
                    performance_tier=tier.performance_tier,
                )
                team_id = _game_team_for_player(db, rating.player_id)
                rows.append(
                    {
                        "role": rating.role,
                        "decision": assessment.decision,
                        "reasons": assessment.reasons,
                        "evidence": assessment.evidence,
                        "rarity": rarity.name,
                        "team_id": team_id,
                    }
                )

            # ---- 3. agregados ------------------------------------------------
            buckets = {
                role: Counter(r["decision"] for r in rows if r["role"] == role)
                for role in ROLES
            }
            report["buckets"] = {
                "totals": dict(Counter(r["decision"] for r in rows)),
                "by_role": {role: dict(buckets[role]) for role in ROLES},
            }

            ineligible_drivers = defaultdict(Counter)
            for r in rows:
                if r["decision"] != INELIGIBLE:
                    continue
                for attribute, assessment in r["evidence"].attributes.items():
                    if assessment.status == "BELOW_THRESHOLD":
                        ineligible_drivers[r["role"]][attribute] += 1
            report["ineligible_drivers"] = {
                role: dict(counter) for role, counter in ineligible_drivers.items()
            }

            attribute_status = defaultdict(Counter)
            for r in rows:
                for attribute, assessment in r["evidence"].attributes.items():
                    attribute_status[attribute][assessment.status] += 1
            report["attribute_status"] = {
                attribute: dict(counter) for attribute, counter in attribute_status.items()
            }

            role_rows = {role: [r for r in rows if r["role"] == role] for role in ROLES}
            sensitivity = {}
            for role in ROLES:
                if not role_rows[role]:
                    continue
                available = {
                    a for a in role_rows[role][0]["evidence"].attributes
                }
                role_sensitivity = {}
                for attribute in sorted(CALIBRATED_THRESHOLDS.keys() & available):
                    values = [
                        r["evidence"].attributes[attribute].evidence
                        for r in role_rows[role]
                        if r["evidence"].attributes[attribute].evidence is not None
                    ]
                    if not values:
                        continue
                    current_threshold = CALIBRATED_THRESHOLDS[attribute]
                    role_sensitivity[attribute] = {
                        "count": len(values),
                        "below_current_threshold": sum(
                            1 for v in values if v < current_threshold
                        ),
                        "pct_by_candidate": {
                            str(t): _round(100 * sum(1 for v in values if v < t) / len(values))
                            for t in thresholds
                        },
                    }
                sensitivity[role] = role_sensitivity
            report["sensitivity"] = sensitivity

            report["bucket_x_rarity"] = {
                role: {
                    decision: {
                        rarity_key: sum(
                            1
                            for r in rows
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
            for r in rows:
                team_impact[r["team_id"] or "sin_team"][r["decision"]] += 1
            team_summary = []
            for team_id, decisions in team_impact.items():
                team_summary.append(
                    {
                        "team_id": team_id,
                        "total": sum(decisions.values()),
                        "decisions": dict(decisions),
                    }
                )
            team_summary.sort(
                key=lambda t: (
                    -t["decisions"].get(INELIGIBLE, 0),
                    -t["total"],
                )
            )
            report["team_impact_top"] = team_summary[: args.top_teams]

            print(json.dumps(report, default=_json_default, indent=2))
        except Exception as exc:  # noqa: BLE001 - el reporte es la entrega
            return_code = 1
            print(json.dumps({"error": repr(exc)}, default=_json_default, indent=2))
        finally:
            conn.rollback()

    after = SessionLocal().query(RatingDistribution).count()
    integrity = {
        "rating_distributions_before": before,
        "rating_distributions_after": after,
        "clean": before == after,
    }
    print(json.dumps({"rollback_integrity": integrity}, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())