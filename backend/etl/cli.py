"""CLI del ETL (spec §35).

Uso (desde backend/):  python -m etl.cli <subcomando> --opciones
"""

import argparse
import logging
from datetime import date

from app.database import SessionLocal
from etl.pipelines.analytics import AnalyticsPipeline
from etl.pipelines.metadata import MetadataPipeline
from etl.pipelines.statcast import StatcastRawPipeline
from etl.services.card_profiles import generate_profiles
from etl.services.quality import collect_quality, emit_quality_report
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

    imp = sub.add_parser("import-players", help="Importa metadata MLB (equipos/rosters)")
    imp.add_argument("--season", type=int, default=_default_season())
    imp.add_argument("--start", type=_parse_date)
    imp.add_argument("--end", default=None)

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

    an = sub.add_parser("build-analytics", help="Regenera perfiles analytics del snapshot")
    an.add_argument("--season", type=int, required=True)
    an.add_argument("--data-start-date", dest="data_start_date", type=_parse_date, required=True)
    an.add_argument("--data-end-date", dest="data_end_date", type=_parse_date, required=True)

    run = sub.add_parser("run", help="Pipeline completo")
    run.add_argument("--season", type=int, required=True)
    run.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    run.add_argument("--to", dest="date_to", type=_parse_date, required=True)

    gen = sub.add_parser("generate-profiles", help="Genera CardGenerationProfile")
    gen.add_argument("--season", type=int, required=True)

    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    db = SessionLocal()
    try:
        if args.command == "import-players":
            start = args.start or date(args.season, 1, 1)
            end = _parse_date(args.end) if args.end else date(args.season, 12, 31)
            client = MLBStatsApiClient()
            result = MetadataPipeline(db, client).run_teams_and_rosters(
                season=args.season, data_start_date=start, data_end_date=end
            )
            logger.info("metadata teams=%s players=%s unresolved=%s", result.teams, len(result.unresolved), result.unresolved)

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

        elif args.command == "build-analytics":
            pipeline = AnalyticsPipeline(db)
            result = pipeline.rebuild(
                season=args.season, data_start_date=args.data_start_date, data_end_date=args.data_end_date
            )
            logger.info("analytics players=%s profiles=%s rejected=%s", result.players_processed, result.profiles_created, result.analytics_rejected)

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

        elif args.command == "generate-profiles":
            result = generate_profiles(db, season=args.season)
            logger.info("card profiles created=%s skipped=%s version=%s", result.created, result.skipped, result.version)

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