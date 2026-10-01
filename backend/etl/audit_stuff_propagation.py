"""DATA-STUFF-001A — auditoría read-only de propagación de Stuff (ACTIVE BASE v2).

Pregunta que responde (roadmap §32 paso 1, §36):

    de las 806 cartas ACTIVE del catálogo BASE v2 (ratings-2.0),
    ¿cuántas tienen card.stuff = 70 mientras el Stuff autoritativo
    (ratings-2.0) != 70?

    el motor habla Stuff pero el catálogo lo silencia.

Por qué puede ocurrir
--------------------
`etl/services/card_catalog.py::_card_from_profile` lee `stuff_rating` dentro de
`_RATING_FIELDS` y lo materializa en `values`, pero el constructor de
`PlayerCardModel` de esa misma función nunca asigna `stuff`. Toda carta
publicada queda en el `default=70` / `server_default='70'` de la migración
0042, es decir Stuff exactamente neutro para toda la flota.

Alcance y por qué es sólo de pitchers
-------------------------------------
`stuff` es un atributo de PITCHER. Los CHECK de role-shape
(`ck_card_rating_profiles_complete_role_shape` y
`ck_player_ratings_complete_role_shape`) fuerzan `stuff_rating IS NULL` para
BATTER, así que una carta de bateo con `stuff = 70` NO es un silencio: es el
único valor que puede tener. Contar las 806 cartas como una sola población
produciría ~402 "mismatches" falsos. Por eso la auditoría segmenta por role y
el contrato crítico (silent_default_mismatch) se mide sobre pitchers.

La auditoría detecta si la columna `player_cards.stuff` existe (migración
0042). Si la DB está por detrás del head, la clasificación de las cartas cae a
`column_absent` y el reporte lo declara en `schema` en vez de fallar en
silencio.

Precedencia auditada (idéntica a `app/seeds/backfill_cards.py`)

    1. CardRatingProfile.stuff_rating     (fuente autoritativa de la carta)
    2. PlayerRatings.stuff_rating         (PITCHER, mismo player + season,
                                           corte más reciente por updated_at)
    3. STUFF_BASELINE (70)                (sin dato: neutro exacto, delta=0)

Seguridad / D6 — read-only
--------------------------
Un único `Connection.begin()`; la Session se une con
`join_transaction_mode="create_savepoint"` y el `finally` hace `rollback()`.
No se emite ni un `INSERT`/`UPDATE`/`DELETE`/`flush` de escritura. Se
verifica además con conteos before/after sobre las tres tablas del universo.

Uso
---
    python -m etl.audit_stuff_propagation
    python -m etl.audit_stuff_propagation --expected-active 806 --sample 25
"""

import argparse
import json
from collections import Counter
from datetime import date
from decimal import Decimal

from sqlalchemy import func, inspect, select, text

from app.database import SessionLocal, engine
from app.engine.stuff_policy import (
    STUFF_BASELINE,
    STUFF_POWER_SUPPRESSION,
    stuff_power_suppression,
)
from app.models import (
    CardCatalog,
    CardEditionType,
    CardRatingProfile,
    PlayerCardModel,
    PlayerRatings,
)

PITCHER_ROLE = "PITCHER"
BATTER_ROLE = "BATTER"
ROLE_UNKNOWN = "UNKNOWN"

SOURCE_PROFILE = "card_rating_profile"
SOURCE_PLAYER_RATINGS = "player_ratings"
SOURCE_BASELINE = "baseline"

CLASS_EXACT = "exact"
CLASS_EXACT_BASELINE = "exact_at_baseline"
CLASS_SILENT_DEFAULT = "silent_default_mismatch"
CLASS_STALE_OVERRIDE = "stale_override"
CLASS_DIVERGENT = "divergent"
CLASS_COLUMN_ABSENT = "column_absent"

# Tablas cuyo conteo se compara antes/después para probar D6.
_UNIVERSE_TABLES = (PlayerCardModel, CardRatingProfile, PlayerRatings)


def _json_default(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _table_count(conn, table) -> int:
    """Conteo por Core (``SELECT count(*)``) en vez de entidad ORM.

    Una entidad ORM genera ``SELECT`` con la lista completa de columnas del
    modelo, que revienta si la DB está por detrás del head de Alembic (aquí
    ``player_cards.stuff``). La auditoría debe poder ejecutarse justo en ese
    estado — es cuando más información aporta.
    """
    return conn.execute(select(func.count()).select_from(table)).scalar()


def _schema_head(conn) -> str:
    return conn.execute(text("select version_num from alembic_version")).scalar()


def _stuff_column_present(conn) -> bool:
    return "stuff" in {
        c["name"] for c in inspect(conn).get_columns(PlayerCardModel.__tablename__)
    }


def _resolve_authoritative_stuff(profile, rating):
    """Devuelve ``(stuff, source)`` con la precedencia documentada.

    Se replica exactamente la precedencia de ``app/seeds/backfill_cards.py``
    para que la auditoría mida la resolución que el motor acabaría
    consumiendo, no una variante de la auditoría.
    """
    if profile is not None and profile["stuff_rating"] is not None:
        return int(profile["stuff_rating"]), SOURCE_PROFILE
    if rating is not None and rating["stuff_rating"] is not None:
        return int(rating["stuff_rating"]), SOURCE_PLAYER_RATINGS
    return STUFF_BASELINE, SOURCE_BASELINE


def _classify(card_stuff: int, authoritative: int) -> str:
    if card_stuff != authoritative:
        if card_stuff == STUFF_BASELINE:
            return CLASS_SILENT_DEFAULT
        if authoritative == STUFF_BASELINE:
            return CLASS_STALE_OVERRIDE
        return CLASS_DIVERGENT
    if card_stuff == STUFF_BASELINE:
        return CLASS_EXACT_BASELINE
    return CLASS_EXACT


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="DATA-STUFF-001A")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--edition-type", default=CardEditionType.BASE.value)
    parser.add_argument("--status", default="ACTIVE")
    parser.add_argument("--expected-active", type=int, default=806)
    parser.add_argument(
        "--sample",
        type=int,
        default=20,
        help="mismatches de ejemplo en el reporte (0 = sin muestra)",
    )
    args = parser.parse_args(argv)

    report: dict = {
        "block": "DATA-STUFF-001A",
        "mutations": "none (read-only)",
        "schema": {},
        "universe": {},
        "counters": {},
        "role_split": {},
        "sources": {},
        "stuff_distribution": {},
        "samples": {},
        "contracts": {},
    }

    with engine.connect() as conn:
        conn.begin()
        before = {
            table.__tablename__: _table_count(conn, table)
            for table in _UNIVERSE_TABLES
        }
        schema_head = _schema_head(conn)
        stuff_column = _stuff_column_present(conn)

        report["schema"] = {
            "alembic_head": schema_head,
            "player_cards_stuff_column": stuff_column,
        }

        try:
            catalog = conn.execute(
                select(
                    CardCatalog.id,
                    CardCatalog.version,
                    CardCatalog.status,
                    CardCatalog.rating_model_version,
                ).where(
                    CardCatalog.season == args.season,
                    CardCatalog.edition_type == args.edition_type,
                    CardCatalog.status == args.status,
                )
            ).mappings().one_or_none()

            if catalog is None:
                report["error"] = (
                    f"no hay catálogo {args.status} {args.season}/{args.edition_type}"
                )
                report["contracts"]["D1"] = {"status": "FAIL", "detail": "universo inexistente"}
                print(json.dumps(report, default=_json_default, indent=2))
                return 1

            card_columns = [
                PlayerCardModel.id,
                PlayerCardModel.name,
                PlayerCardModel.team_id,
                PlayerCardModel.position,
                PlayerCardModel.overall,
                PlayerCardModel.player_id,
                PlayerCardModel.season,
                PlayerCardModel.card_rating_profile_id,
                PlayerCardModel.is_active,
                PlayerCardModel.is_pack_eligible,
            ]
            if stuff_column:
                card_columns.append(PlayerCardModel.stuff)

            cards = (
                conn.execute(
                    select(*card_columns).where(
                        PlayerCardModel.catalog_id == catalog["id"]
                    )
                )
                .mappings()
                .all()
            )

            profile_ids = {c["card_rating_profile_id"] for c in cards if c["card_rating_profile_id"]}
            profiles = {
                row["id"]: row
                for row in conn.execute(
                    select(
                        CardRatingProfile.id,
                        CardRatingProfile.role,
                        CardRatingProfile.stuff_rating,
                    ).where(CardRatingProfile.id.in_(profile_ids))
                )
                .mappings()
                .all()
            }

            # PlayerRatings PITCHER por (player, season), corte más reciente.
            ratings: dict[tuple[str, int], dict] = {}
            for row in conn.execute(
                select(
                    PlayerRatings.id,
                    PlayerRatings.player_id,
                    PlayerRatings.season,
                    PlayerRatings.stuff_rating,
                    PlayerRatings.rating_model_version,
                    PlayerRatings.updated_at,
                )
                .where(
                    PlayerRatings.season == args.season,
                    PlayerRatings.role == PITCHER_ROLE,
                    PlayerRatings.stuff_rating.isnot(None),
                )
                .order_by(PlayerRatings.updated_at.desc())
            ).mappings():
                ratings.setdefault((row["player_id"], row["season"]), row)

            report["universe"] = {
                "catalog_id": catalog["id"],
                "catalog_version": catalog["version"],
                "catalog_status": catalog["status"],
                "catalog_rating_model_version": catalog["rating_model_version"],
                "total_cards": len(cards),
                "expected_total": args.expected_active,
                "total_active": sum(1 for c in cards if c["is_active"]),
                "total_pack_eligible": sum(1 for c in cards if c["is_pack_eligible"]),
            }

            role_split: Counter = Counter()
            sources: Counter = Counter()
            classes: Counter = Counter()
            card_stuff_values: Counter = Counter()
            auth_stuff_values: Counter = Counter()
            deltas: Counter = Counter()
            missing_profile = []
            missing_player_rating = []
            conflicts = []
            silent_defaults = []
            out_of_domain = []

            for card in cards:
                profile = profiles.get(card["card_rating_profile_id"])
                role = profile["role"] if profile is not None else ROLE_UNKNOWN
                role_split[role] += 1

                card_stuff = (
                    int(card["stuff"])
                    if stuff_column and card.get("stuff") is not None
                    else None
                )

                if profile is None:
                    missing_profile.append(
                        {
                            "card_id": card["id"],
                            "name": card["name"],
                            "position": card["position"],
                            "card_rating_profile_id": card["card_rating_profile_id"],
                        }
                    )

                rating = (
                    ratings.get((card["player_id"], card["season"]))
                    if card["player_id"] and card["season"]
                    else None
                )

                if role == PITCHER_ROLE and rating is None:
                    missing_player_rating.append(
                        {
                            "card_id": card["id"],
                            "name": card["name"],
                            "player_id": card["player_id"],
                        }
                    )

                # D4 — conflicto Profile ↔ PlayerRatings (se reporta por
                # separado: no decide precedencia, pero invalida la
                # trazabilidad del corte).
                if (
                    profile is not None
                    and profile["stuff_rating"] is not None
                    and rating is not None
                    and rating["stuff_rating"] is not None
                    and int(profile["stuff_rating"]) != int(rating["stuff_rating"])
                ):
                    conflicts.append(
                        {
                            "card_id": card["id"],
                            "name": card["name"],
                            "card_rating_profile_id": profile["id"],
                            "player_ratings_id": rating["id"],
                            "profile_stuff": int(profile["stuff_rating"]),
                            "player_ratings_stuff": int(rating["stuff_rating"]),
                            "rating_model_version": rating["rating_model_version"],
                        }
                    )

                authoritative, source = _resolve_authoritative_stuff(profile, rating)

                if role == BATTER_ROLE:
                    # Stuff no existe para batters (CHECK role-shape). Se
                    # registra la fuente para visibilidad pero NO cuenta como
                    # mismatch.
                    sources[f"{BATTER_ROLE}:{source}"] += 1
                    if card_stuff is not None:
                        card_stuff_values[card_stuff] += 1
                    continue

                if authoritative < 40 or authoritative > 99:
                    out_of_domain.append(
                        {
                            "card_id": card["id"],
                            "name": card["name"],
                            "authoritative": authoritative,
                        }
                    )

                sources[source] += 1
                if card_stuff is not None:
                    card_stuff_values[card_stuff] += 1
                auth_stuff_values[authoritative] += 1

                if card_stuff is None:
                    classification = CLASS_COLUMN_ABSENT
                else:
                    classification = _classify(card_stuff, authoritative)
                classes[classification] += 1

                if card_stuff is not None:
                    deltas[card_stuff - authoritative] += 1

                if classification in (
                    CLASS_SILENT_DEFAULT,
                    CLASS_STALE_OVERRIDE,
                    CLASS_DIVERGENT,
                ):
                    if args.sample and len(
                        [s for s in silent_defaults if s["_class"] == classification]
                    ) < args.sample:
                        silent_defaults.append(
                            {
                                "_class": classification,
                                "card_id": card["id"],
                                "name": card["name"],
                                "team_id": card["team_id"],
                                "position": card["position"],
                                "overall": card["overall"],
                                "card_stuff": card_stuff,
                                "authoritative_stuff": authoritative,
                                "source": source,
                                "card_suppression": round(
                                    stuff_power_suppression(card_stuff), 4
                                )
                                if card_stuff is not None
                                else None,
                                "authoritative_suppression": round(
                                    stuff_power_suppression(authoritative), 4
                                ),
                                "suppression_gap": round(
                                    stuff_power_suppression(card_stuff)
                                    - stuff_power_suppression(authoritative),
                                    4,
                                )
                                if card_stuff is not None
                                else None,
                            }
                        )

            pitchers = role_split.get(PITCHER_ROLE, 0)

            report["role_split"] = {
                "PITCHER": pitchers,
                "BATTER": role_split.get(BATTER_ROLE, 0),
                "UNKNOWN": role_split.get(ROLE_UNKNOWN, 0),
            }
            report["sources"] = {
                "pitcher": {
                    k: v for k, v in sources.items() if not k.startswith(f"{BATTER_ROLE}:")
                },
                "batter_note": {
                    k: v for k, v in sources.items() if k.startswith(f"{BATTER_ROLE}:")
                },
            }
            report["counters"] = {
                "total_active": report["universe"]["total_active"],
                "total_pitcher_cards": pitchers,
                "stuff_column_eq_70": card_stuff_values.get(STUFF_BASELINE, 0),
                "stuff_column_distinct_values": len(card_stuff_values),
                "authoritative_stuff_eq_70": auth_stuff_values.get(STUFF_BASELINE, 0),
                "authoritative_stuff_distinct_values": len(auth_stuff_values),
                "exact_match": classes[CLASS_EXACT],
                "exact_match_at_baseline": classes[CLASS_EXACT_BASELINE],
                "silent_default_mismatch": classes[CLASS_SILENT_DEFAULT],
                "stale_override": classes[CLASS_STALE_OVERRIDE],
                "divergent": classes[CLASS_DIVERGENT],
                "column_absent": classes[CLASS_COLUMN_ABSENT],
                "missing_profile": len(missing_profile),
                "missing_player_rating": len(missing_player_rating),
                "conflicting_profile_vs_player_rating": len(conflicts),
                "authoritative_out_of_domain": len(out_of_domain),
            }
            report["stuff_distribution"] = {
                "card_stuff": dict(sorted(card_stuff_values.items())),
                "authoritative_stuff": dict(sorted(auth_stuff_values.items())),
                "delta_card_minus_authoritative": dict(sorted(deltas.items())),
            }
            report["samples"] = {
                "mismatches": sorted(silent_defaults, key=lambda s: s["_class"]),
                "missing_profile": missing_profile[: args.sample] if args.sample else [],
                "conflicting_profile_vs_player_rating": (
                    conflicts[: args.sample] if args.sample else []
                ),
            }

            critical = classes[CLASS_SILENT_DEFAULT]
            resolved = classes[CLASS_EXACT] + classes[CLASS_EXACT_BASELINE]

            report["contracts"] = {
                "D1": {
                    "statement": f"universo == {args.expected_active} cartas ACTIVE",
                    "observed": report["universe"]["total_active"],
                    "status": "PASS"
                    if report["universe"]["total_active"] == args.expected_active
                    else "FAIL",
                },
                "D2": {
                    "statement": "cada carta de pitcher resuelve un Stuff autoritativo único y en dominio",
                    "observed": f"{pitchers - len(out_of_domain)}/{pitchers}",
                    "status": "PASS" if not out_of_domain else "FAIL",
                },
                "D3": {
                    "statement": "las fuentes faltantes se reportan",
                    "observed": {
                        "missing_profile": len(missing_profile),
                        "missing_player_rating": len(missing_player_rating),
                        "fallback_to_baseline": classes[CLASS_EXACT_BASELINE],
                    },
                    "status": "PASS",
                },
                "D4": {
                    "statement": "los conflictos Profile ↔ PlayerRatings se reportan por separado",
                    "observed": len(conflicts),
                    "status": "PASS",
                },
                "D5": {
                    "statement": "matches exactos y silent-default mismatches se clasifican",
                    "observed": {
                        "exact": classes[CLASS_EXACT],
                        "exact_at_baseline": classes[CLASS_EXACT_BASELINE],
                        "silent_default_mismatch": critical,
                        "stale_override": classes[CLASS_STALE_OVERRIDE],
                        "divergent": classes[CLASS_DIVERGENT],
                    },
                    "status": "PASS",
                },
                "D6": {
                    "statement": "la auditoría es read-only",
                    # Se verifica abajo con los conteos before/after; no se
                    # declara PASS por construcción. Un contrato que se afirma a
                    # sí mismo no es evidencia.
                    "observed": None,
                    "status": "PENDING",
                },
                "D7": {
                    "statement": "sin mutaciones hasta caracterizar la población",
                    "observed": "no backfill ejecutado por este script",
                    "status": "PASS",
                },
            }

            if not stuff_column:
                branch = "BLOCKED: falta la columna player_cards.stuff (migración 0042)"
                schema_ok = False
            elif critical > 0:
                branch = "DATA-STUFF-001B"
                schema_ok = True
            else:
                branch = "CLOSE DATA-STUFF-001"
                schema_ok = True

            report["verdict"] = {
                "alembic_head": schema_head,
                "player_cards_stuff_column": stuff_column,
                "silent_default_mismatch": critical,
                "pitcher_cards": pitchers,
                "pitcher_cards_materialized": resolved,
                "materialization_rate": round(resolved / pitchers, 6) if pitchers else None,
                "branch": branch,
                "stuff_policy": {
                    "baseline": STUFF_BASELINE,
                    "power_suppression": STUFF_POWER_SUPPRESSION,
                },
            }
        finally:
            conn.rollback()

        after = {
            table.__tablename__: _table_count(conn, table)
            for table in _UNIVERSE_TABLES
        }

    report["rollback_integrity"] = {
        "before": before,
        "after": after,
        "clean": before == after,
    }

    # D6 se resuelve con la evidencia, no se declara.
    clean = before == after
    report["contracts"]["D6"]["observed"] = {
        "strategy": "rollback-only, sin sentencias de escritura",
        "table_counts_unchanged": clean,
        "detail": "conteos before/after idénticos sobre player_cards, "
        "card_rating_profiles y player_ratings"
        if clean
        else "los conteos cambiaron: la auditoría NO fue read-only",
    }
    report["contracts"]["D6"]["status"] = "PASS" if clean else "FAIL"

    # D7 depende de la misma evidencia: si la auditoría hubiera escrito, la
    # población quedaría caracterizada *y* mutada, que es exactamente lo que
    # 001A prohíbe.
    report["contracts"]["D7"]["observed"] = (
        "ninguna escritura emitida; la mutación queda para 001B"
        if clean
        else "la auditoría escribió: 001A queda invalidado"
    )
    report["contracts"]["D7"]["status"] = "PASS" if clean else "FAIL"

    print(json.dumps(report, default=_json_default, indent=2))

    contracts = report["contracts"]
    all_pass = all(c.get("status") == "PASS" for c in contracts.values())
    return 0 if all_pass and schema_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())