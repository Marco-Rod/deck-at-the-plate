"""CLI del ETL (spec §35).

Uso (desde backend/):  python -m etl.cli <subcomando> --opciones
"""

import argparse
import logging
from datetime import date
from datetime import timedelta

from app.database import SessionLocal
from etl.http.client import ExternalHttpClient
from etl.sources.mlb import MLBStatsApiClient
from etl.sources.statcast import StatcastSourceAdapter
from etl.pipelines.metadata import MetadataPipeline
from etl.pipelines.statcast import StatcastRawPipeline
from etl.pipelines.analytics import AnalyticsPipeline
from etl.services.card_profiles import ProfileRunResult, generate_profiles
from etl.services.quality import QualitySummary, collect_quality, emit_quality_report

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


def _summary(result, source: str) -> QualitySummary:
    summary = QualitySummary()
    summary.source = source
    if hasattr(result, "import_run_id"):
        summary.run_id = result.import_run_id
    return summary


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
            version = args.role
            # Resolver metadata del jugador primero (nunca hardcodear mlb_id aquí).
            from etl.sources.mlb import PlayerMetadataCache

            client = MLBStatsApiClient()
            cache = PlayerMetadataCache(client)
            record = cache.get_player(args.player_id)
            if record is None:
                logger.error("mlb_id sin resolver: %s", args.player_id)
                return 2
            from etl.loaders.core import upsert_player, upsert_player_season

            player = upsert_player(db, record)
            upsert_player_season(db, player=player, season=args.date_from.year, data_start_date=args.date_from, data_end_date=args.date_to)
            db.commit()

            if args.role == "batter":
                records = adapter.fetch_batter(args.player_id, args.date_from, args.date_to)
            else:
                records = adapter.fetch_pitcher(args.player_id, args.date_from, args.date_to)
            from etl.normalizers.raw_mapper import normalize_row
            from etl.validators.raw import validate_raw_row
            from etl.pipelines.statcast import StatcastRunResult
            from etl.loaders.raw import upsert_raw_pitch_events
            from app.core.enums import ImportStatus
            from app.models import DataImportRun
            from app.core.time import utcnow

            run = DataImportRun(source="STATCAST", pipeline_version="1.0.0", season=args.date_from.year, date_from=args.date_from, date_to=args.date_to, status=ImportStatus.RUNNING)
            db.add(run)
            db.commit()
            result = StatcastRunResult(rows_extracted=len(records))
            rows = []
            rejected = 0
            for rec in records:
                errors = validate_raw_row(rec)
                if errors:
                    rejected += 1
                    continue
                rows.append(normalize_row(rec))
            upsert = upsert_raw_pitch_events(db, import_run_id=run.id, rows=rows, refresh=args.refresh)
            result.rows_inserted = upsert.inserted
            result.rows_updated = upsert.updated
            result.rows_rejected = rejected
            run.rows_extracted = result.rows_extracted
            run.rows_inserted = upsert.inserted
            run.rows_updated = upsert.updated
            run.rows_rejected = rejected
            run.status = ImportStatus.SUCCESS
            run.finished_at = utcnow()
            db.commit()
            logger.info("statcast-player inserted=%s updated=%s rejected=%s", upsert.inserted, upsert.updated, rejected)

        elif args.command == "build-analytics":
            pipeline = AnalyticsPipeline(db)
            result = pipeline.rebuild(
                season=args.season, data_start_date=args.data_start_date, data_end_date=args.data_end_date
            )
            logger.info("analytics players=%s profiles=%s rejected=%s", result.players_processed, result.profiles_created, result.analytics_rejected)

        elif args.command == "run":
            adapter = StatcastSourceAdapter()
            raw = StatcastRawPipeline(db, adapter).run(date_from=args.date_from, date_to=args.date_to, season=args.season)
            logger.info("raw done inserted=%s", raw.rows_inserted)
            # Analytics para el snapshot completo de la temporada.
            analytics = AnalyticsPipeline(db).rebuild(season=args.season, data_start_date=date(args.season, 1, 1), data_end_date=args.date_to)
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