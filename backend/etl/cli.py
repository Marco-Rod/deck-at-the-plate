"""CLI del ETL (spec §35, plan V2).

Uso (desde backend/):  python -m etl.cli <subcomando> --opciones

V2.1 — primera carga completa (receta, §47/§82/§92):
    python -m etl.cli sync-source-teams --season 2026
    python -m etl.cli sync-game-team-mappings --season 2026
    python -m etl.cli sync-rosters --season 2026
    python -m etl.cli generate-game-identities --season 2026 --dry-run --report   # revisar QA
    python -m etl.cli generate-game-identities --season 2026 --missing-only
    python -m etl.cli validate-game-identities --season 2026
    python -m etl.cli generate-card-profiles --season 2026
    python -m etl.cli validate-card-profiles --season 2026
    python -m etl.cli publish-card-catalog --season 2026
    python -m etl.cli validate-cpu-rosters --season 2026
    python -m etl.cli validate-pack-pool --season 2026
La identidad pública (display_*) jamás expone el nombre fuente real (§88); el
reporte QA es administrativo (§81).
"""

import argparse
import logging
from datetime import date

from app.database import SessionLocal
from etl.config import NAMES_GENERATOR_VERSION, RATING_MODEL_VERSION
from etl.pipelines.analytics import AnalyticsPipeline
from etl.pipelines.metadata import MetadataPipeline
from etl.pipelines.statcast import StatcastRawPipeline
from etl.services.card_catalog import publish_card_catalog, validate_cpu_rosters, validate_pack_pool
from etl.services.card_profiles import generate_profiles, validate_profiles
from etl.services.identity_generation import validate_game_identities
from etl.services.league_distributions import build_league_distributions
from etl.services.quality import collect_quality, emit_quality_report
from etl.services.statcast_population import import_statcast_population
from etl.sources.mlb import MLBStatsApiClient
from etl.sources.statcast import StatcastSourceAdapter

logger = logging.getLogger("etl.cli")


def _default_season() -> int:
    return date.today().year


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="etl.cli", description="Deck at the Plate ETL")
    sub = parser.add_subparsers(dest="command", required=True)

    st = sub.add_parser("sync-source-teams", help="Capa SOURCE: franquicias reales MLB (30)")
    st.add_argument("--season", type=int, default=_default_season())

    gm = sub.add_parser("sync-game-team-mappings", help="Capa GAME: franquicias públicas + mapping SOURCE<->GAME")
    gm.add_argument("--season", type=int, default=_default_season())

    gi = sub.add_parser("generate-game-identities", help="Crea identidades públicas ficticias de jugadores")
    gi.add_argument("--season", type=int, default=None)
    gi.add_argument("--all", action="store_true", help="Regenera todas (default: solo faltantes)")
    gi.add_argument("--missing-only", action="store_true", help="Solo faltantes (default)")
    gi.add_argument("--generator-version", dest="generator_version", default=None, help="Versión de pools names-* (*default: names-1.0)")
    gi.add_argument("--dry-run", action="store_true", help="Calcula candidatos y reporta sin escribir en BD")
    gi.add_argument("--player-id", dest="player_id", type=int, default=None, help="Filtra por mlb_id")
    gi.add_argument("--limit", type=int, default=None, help="Límite de jugadores del batch")
    gi.add_argument("--report", action="store_true", help="Imprime el reporte QA completo")

    vig = sub.add_parser("validate-game-identities", help="Valida identidades GAME (gate §83)")
    vig.add_argument("--season", type=int, default=None)
    vig.add_argument("--generator-version", dest="generator_version", default=None)

    sr = sub.add_parser("sync-rosters", help="Sincroniza rosters (players+snapshots SOURCE)")
    sr.add_argument("--season", type=int, default=_default_season())
    sr.add_argument("--start", type=_parse_date)
    sr.add_argument("--end", type=_parse_date, default=None)

    st = sub.add_parser("import-statcast", help="Ingiere RawPitchEvent por rango")
    st.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    st.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    st.add_argument("--season", type=int, default=None)
    st.add_argument("--refresh", action="store_true")

    stp = sub.add_parser("import-statcast-player", help="Ingiere pitches de un jugador")
    stp.add_argument("--player-id", dest="player_id", type=int, required=True)
    stp.add_argument("--role", choices=("batter", "pitcher"), default="batter")
    stp.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    stp.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    stp.add_argument("--refresh", action="store_true")

    pop = sub.add_parser("import-statcast-population", help="Ingiere Statcast para una población SOURCE")
    pop.add_argument("--season", type=int, required=True)
    pop.add_argument("--role", choices=("pitcher",), default="pitcher")
    pop.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    pop.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    pop.add_argument("--limit", type=int, default=40)
    pop.add_argument("--refresh", action="store_true")

    an = sub.add_parser("build-analytics", help="Regenera perfiles analytics del snapshot")
    an.add_argument("--season", type=int, required=True)
    an.add_argument("--data-start-date", dest="data_start_date", type=_parse_date, required=True)
    an.add_argument("--data-end-date", dest="data_end_date", type=_parse_date, required=True)

    dist = sub.add_parser("build-league-distributions", help="Construye distribuciones versionadas desde Analytics")
    dist.add_argument("--season", type=int, required=True)
    dist.add_argument("--role", choices=("pitcher",), default="pitcher")
    dist.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    dist.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    dist.add_argument("--distribution-version", dest="distribution_version", default=None)

    run = sub.add_parser("run", help="Pipeline completo")
    run.add_argument("--season", type=int, required=True)
    run.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    run.add_argument("--to", dest="date_to", type=_parse_date, required=True)

    gen = sub.add_parser("generate-card-profiles", help="Genera CardGenerationProfile (gate previo a publicar)")
    gen.add_argument("--season", type=int, required=True)
    gen.add_argument("--data-end-date", dest="data_end_date", type=_parse_date, default=None)
    gen.add_argument(
        "--rating-model",
        dest="rating_model",
        type=str,
        default=RATING_MODEL_VERSION,
    )

    val = sub.add_parser("validate-card-profiles", help="Valida perfiles (gate §52)")
    val.add_argument("--season", type=int, required=True)
    val.add_argument("--data-end-date", dest="data_end_date", type=_parse_date, default=None)
    val.add_argument(
        "--rating-model",
        dest="rating_model",
        type=str,
        default=RATING_MODEL_VERSION,
    )

    pub = sub.add_parser("publish-card-catalog", help="Publica el catálogo (BUILDING→VALIDATING→ACTIVE)")
    pub.add_argument("--season", type=int, required=True)
    pub.add_argument("--edition", default="BASE")
    pub.add_argument("--data-end-date", dest="data_end_date", type=_parse_date, default=None)
    pub.add_argument(
        "--rating-model",
        dest="rating_model",
        type=str,
        default=RATING_MODEL_VERSION,
    )

    vcpu = sub.add_parser("validate-cpu-rosters", help="Valida rosters CPU derivados (§53)")
    vcpu.add_argument("--season", type=int, required=True)
    vcpu.add_argument("--edition", default="BASE")

    vpk = sub.add_parser("validate-pack-pool", help="Valida el pack pool del catálogo ACTIVE (§54)")
    vpk.add_argument("--season", type=int, required=True)
    vpk.add_argument("--edition", default="BASE")

    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    db = SessionLocal()
    try:
        if args.command == "sync-source-teams":
            client = MLBStatsApiClient()
            result = MetadataPipeline(db, client).run_source_teams(season=args.season)
            logger.info("sync-source-teams source_teams=%s", result.source_teams)

        elif args.command == "sync-game-team-mappings":
            client = MLBStatsApiClient()
            result = MetadataPipeline(db, client).run_game_team_mappings(season=args.season)
            logger.info(
                "sync-game-team-mappings source_teams=%s game_teams=%s",
                result.source_teams, result.game_teams,
            )

        elif args.command == "generate-game-identities":
            client = MLBStatsApiClient()
            result = MetadataPipeline(db, client).run_game_identities(
                season=args.season,
                missing_only=args.missing_only or not args.all,
                dry_run=args.dry_run,
                generator_version=args.generator_version,
                player_id=args.player_id,
                limit=args.limit,
            )
            if args.dry_run or args.report:
                from etl.services.identity_generation import render_report

                print(render_report(result))
            logger.info(
                "generate-game-identities dry_run=%s created=%s unchanged=%s version=%s",
                result.dry_run, result.created, result.unchanged, result.version,
            )

        elif args.command == "validate-game-identities":
            result = validate_game_identities(db, season=args.season, generator_version=args.generator_version or NAMES_GENERATOR_VERSION)
            logger.info("validate-game-identities ok=%s detail=%s", result.ok, result.detail)
            if not result.ok:
                return 1

        elif args.command == "sync-rosters":
            start = args.start or date(args.season, 1, 1)
            end = args.end or date(args.season, 12, 31)
            client = MLBStatsApiClient()
            result = MetadataPipeline(db, client).run_rosters(
                season=args.season, data_start_date=start, data_end_date=end
            )
            logger.info(
                "sync-rosters players=%s stints=%s snapshots=%s members=%s unresolved=%s",
                result.players,
                result.stints,
                result.roster_snapshots,
                result.roster_members,
                result.unresolved,
            )

        elif args.command == "import-statcast":
            adapter = StatcastSourceAdapter()
            pipeline = StatcastRawPipeline(db, adapter)
            result = pipeline.run(
                date_from=args.date_from, date_to=args.date_to, season=args.season, refresh=args.refresh
            )
            summary = collect_quality(run_result=result, unknown_pitch_types=result.rejection_details)
            emit_quality_report(summary)
            logger.info("statcast inserted=%s updated=%s rejected=%s", result.rows_inserted, result.rows_updated, result.rows_rejected)

        elif args.command == "import-statcast-player":
            adapter = StatcastSourceAdapter()
            client = MLBStatsApiClient()
            metadata = MetadataPipeline(db, client)
            meta_result = metadata.run_season_snapshot_for(
                args.player_id,
                season=args.date_from.year,
                data_start_date=args.date_from,
                data_end_date=args.date_to,
            )
            raw = StatcastRawPipeline(db, adapter).run_player(
                mlb_id=args.player_id,
                role=args.role,
                date_from=args.date_from,
                date_to=args.date_to,
                refresh=args.refresh,
            )
            logger.info(
                "statcast-player role=%s mlb_id=%s metadata_players=%s inserted=%s updated=%s rejected=%s",
                args.role,
                args.player_id,
                meta_result.players,
                raw.rows_inserted,
                raw.rows_updated,
                raw.rows_rejected,
            )

        elif args.command == "import-statcast-population":
            result = import_statcast_population(
                db,
                StatcastSourceAdapter(),
                season=args.season,
                role=args.role,
                date_from=args.date_from,
                date_to=args.date_to,
                limit=args.limit,
                refresh=args.refresh,
            )
            logger.info(
                "statcast-population selected=%s completed=%s no_data=%s failed=%s "
                "extracted=%s inserted=%s updated=%s unchanged=%s rejected=%s",
                result.players_selected,
                result.players_completed,
                result.players_no_data,
                result.players_failed,
                result.rows_extracted,
                result.rows_inserted,
                result.rows_updated,
                result.rows_unchanged,
                result.rows_rejected,
            )
            for failure in result.failures:
                logger.warning("statcast-population failed mlb_id=%s error=%s", failure.mlb_id, failure.error)

        elif args.command == "build-analytics":
            pipeline = AnalyticsPipeline(db)
            result = pipeline.rebuild(
                season=args.season, data_start_date=args.data_start_date, data_end_date=args.data_end_date
            )
            logger.info("analytics players=%s profiles=%s rejected=%s", result.players_processed, result.profiles_created, result.analytics_rejected)

        elif args.command == "build-league-distributions":
            result = build_league_distributions(
                db,
                season=args.season,
                role=args.role,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            logger.info(
                "league distributions created=%s updated=%s unchanged=%s skipped=%s version=%s",
                result.created, result.updated, result.unchanged, result.skipped, result.version,
            )

        elif args.command == "run":
            # Corrección A2: si RAW falla, run() propaga la excepción y aquí se
            # corta la cadena (no se ejecutan metadata ni analytics).
            adapter = StatcastSourceAdapter()
            raw = StatcastRawPipeline(db, adapter).run(
                date_from=args.date_from, date_to=args.date_to, season=args.season
            )
            logger.info("raw done source=%s inserted=%s updated=%s rejected=%s", raw.import_run_id, raw.rows_inserted, raw.rows_updated, raw.rows_rejected)

            # Corrección §6: resolver SOLO los Players presentes en el RAW (sin rosters).
            client = MLBStatsApiClient()
            meta = MetadataPipeline(db, client).resolve_players_from_raw(
                season=args.season, data_start_date=args.date_from, data_end_date=args.date_to
            )
            logger.info("players resolve=%s unresolved=%s", meta.players, meta.unresolved)

            # Analytics sobre el snapshot completo de la temporada.
            analytics = AnalyticsPipeline(db).rebuild(
                season=args.season, data_start_date=date(args.season, 1, 1), data_end_date=args.date_to
            )
            logger.info("analytics players=%s profiles=%s", analytics.players_processed, analytics.profiles_created)

        elif args.command == "generate-card-profiles":
            result = generate_profiles(
                db, season=args.season,
                rating_model_version=args.rating_model,
                data_end_date=args.data_end_date,
            )
            logger.info(
                "card profiles created=%s updated=%s unchanged=%s "
                "skipped_no_data=%s rejected=%s version=%s",
                result.created,
                result.updated,
                result.unchanged,
                result.skipped_no_data,
                result.rejected,
                result.version,
            )

        elif args.command == "validate-card-profiles":
            result = validate_profiles(
                db, season=args.season,
                rating_model_version=args.rating_model,
                data_end_date=args.data_end_date,
            )
            logger.info("validate-card-profiles ok=%s detail=%s", result.ok, result.detail)

        elif args.command == "publish-card-catalog":
            result = publish_card_catalog(
                db, season=args.season,
                edition_type=args.edition,
                rating_model_version=args.rating_model,
                data_end_date=args.data_end_date,
            )
            logger.info(
                "publish-card-catalog status=%s version=%s cards=%s issues=%s",
                result.status, result.catalog_version, result.created, result.issues,
            )

        elif args.command == "validate-cpu-rosters":
            result = validate_cpu_rosters(db, season=args.season, edition_type=args.edition)
            logger.info("validate-cpu-rosters ok=%s detail=%s", result.ok, result.detail)

        elif args.command == "validate-pack-pool":
            result = validate_pack_pool(db, season=args.season, edition_type=args.edition)
            logger.info("validate-pack-pool ok=%s detail=%s", result.ok, result.detail)

        db.close()
        return 0
    except Exception as exc:
        logger.exception("etl falló")
        db.close()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
