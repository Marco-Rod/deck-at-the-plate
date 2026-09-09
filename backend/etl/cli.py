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
from app.services.card_editions import ensure_system_base_edition
from etl.services.card_catalog import (
    publish_card_catalog,
    validate_cpu_rosters,
    validate_pack_pool,
)
from etl.services.card_profiles import generate_profiles, validate_profiles
from etl.services.identity_generation import validate_game_identities
from etl.services.league_distributions import build_league_distributions
from etl.services.quality import collect_quality, emit_quality_report
from etl.services.statcast_population import import_statcast_population
from etl.services.statcast_backfill import backfill_statcast
from etl.services.pitcher_movement import calculate_movement_candidate
from etl.services.pitcher_control import calculate_control_candidate
from etl.services.pitcher_velocity import calculate_velocity_candidate
from etl.services.pitcher_stuff import calculate_stuff_candidate
from etl.services.pitcher_ratings2 import calculate_pitcher_ratings2
from etl.services.player_ratings import persist_batter_ratings2, persist_pitcher_ratings2
from etl.services.ratings2_card_profiles import generate_card_profile_from_ratings2
from etl.services.rating_distributions import build_overall_rating_distribution
from etl.services.pitcher_ratings2_population import generate_pitcher_ratings2_population
from etl.services.batter_contact import calculate_batter_contact
from etl.services.batter_power import calculate_batter_power
from etl.services.batter_vision import calculate_batter_vision
from etl.services.batter_ratings2 import calculate_batter_ratings2
from etl.services.batter_ratings2_population import generate_batter_ratings2_population
from etl.services.player_ratings_as_of import generate_player_ratings_as_of
from etl.services.multi_hr_game_detector import detect_multi_hr_games
from etl.services.ten_strikeout_game_detector import detect_ten_strikeout_games
from etl.services.ten_strikeout_moment_evaluations import (
    evaluate_discovered_ten_strikeout_moments,
)
from etl.services.multi_hr_moment_evaluations import (
    evaluate_discovered_multi_hr_moments,
)
from etl.services.multi_hr_moment_card_profiles import (
    generate_multi_hr_moment_card_profiles,
)
from etl.services.ten_strikeout_moment_card_profiles import (
    generate_ten_strikeout_moment_card_profiles,
)
from etl.services.walk_off_hr_detector import detect_walk_off_home_runs
from etl.services.walk_off_hr_pipeline import run_walk_off_hr_pipeline
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
    pop.add_argument("--role", choices=("batter", "pitcher"), default="pitcher")
    pop.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    pop.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    pop.add_argument("--limit", type=int, default=40)
    pop.add_argument("--refresh", action="store_true")

    backfill = sub.add_parser(
        "backfill-statcast",
        help="Ingiere Statcast histórico para una población desde Opening Day",
    )
    backfill.add_argument("--season", type=int, required=True)
    backfill.add_argument(
        "--role", choices=("batter", "pitcher"), required=True
    )
    backfill.add_argument("--to", dest="date_to", type=_parse_date, required=True)
    backfill.add_argument("--limit", type=int, default=None)
    backfill.add_argument("--refresh", action="store_true")

    an = sub.add_parser("build-analytics", help="Regenera perfiles analytics del snapshot")
    an.add_argument("--season", type=int, required=True)
    an.add_argument("--data-start-date", dest="data_start_date", type=_parse_date, required=True)
    an.add_argument("--data-end-date", dest="data_end_date", type=_parse_date, required=True)

    dist = sub.add_parser("build-league-distributions", help="Construye distribuciones versionadas desde Analytics")
    dist.add_argument("--season", type=int, required=True)
    dist.add_argument("--role", choices=("batter", "pitcher"), default="pitcher")
    dist.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    dist.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    dist.add_argument("--distribution-version", dest="distribution_version", default=None)

    rating_dist = sub.add_parser(
        "build-rating-distributions",
        aliases=["build-rating-distribution"],
        help="Construye distribuciones para tiers relativos de performance",
    )
    rating_dist.add_argument("--season", type=int, required=True)
    rating_dist.add_argument("--role", choices=("batter", "pitcher"), default="pitcher")
    rating_dist.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    rating_dist.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    rating_dist.add_argument("--rating-model-version", dest="rating_model_version", default="ratings-2.0")
    rating_dist.add_argument("--source-distribution-version", dest="source_distribution_version", default=None)
    rating_dist.add_argument(
        "--performance-tier-model-version",
        "--rarity-model-version",
        dest="performance_tier_model_version",
        default="rarity-2.0",
        help="Versión del tier de performance (el segundo nombre es legacy)",
    )

    movement = sub.add_parser("calculate-pitcher-movement", help="Inspecciona candidato Movement sin persistir carta")
    movement.add_argument("--player-id", dest="player_id", type=int, required=True)
    movement.add_argument("--season", type=int, required=True)
    movement.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    movement.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    movement.add_argument("--distribution-version", dest="distribution_version", default=None)

    control = sub.add_parser("calculate-pitcher-control", help="Inspecciona candidato Control sin persistir carta")
    control.add_argument("--player-id", dest="player_id", type=int, required=True)
    control.add_argument("--season", type=int, required=True)
    control.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    control.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    control.add_argument("--distribution-version", dest="distribution_version", default=None)

    velocity = sub.add_parser("calculate-pitcher-velocity", help="Inspecciona candidato Velocity sin persistir carta")
    velocity.add_argument("--player-id", dest="player_id", type=int, required=True)
    velocity.add_argument("--season", type=int, required=True)
    velocity.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    velocity.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    velocity.add_argument("--distribution-version", dest="distribution_version", default=None)

    stuff = sub.add_parser("calculate-pitcher-stuff", help="Inspecciona candidato Stuff sin persistir carta")
    stuff.add_argument("--player-id", dest="player_id", type=int, required=True)
    stuff.add_argument("--season", type=int, required=True)
    stuff.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    stuff.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    stuff.add_argument("--distribution-version", dest="distribution_version", default=None)

    batter_contact = sub.add_parser(
        "calculate-batter-contact",
        help="Inspecciona candidato Contact de batter sin persistir",
    )
    batter_contact.add_argument("--player-id", dest="player_id", type=int, required=True)
    batter_contact.add_argument("--season", type=int, required=True)
    batter_contact.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    batter_contact.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    batter_contact.add_argument("--distribution-version", dest="distribution_version", default=None)

    batter_power = sub.add_parser(
        "calculate-batter-power",
        help="Inspecciona candidato Power de batter sin persistir",
    )
    batter_power.add_argument("--player-id", dest="player_id", type=int, required=True)
    batter_power.add_argument("--season", type=int, required=True)
    batter_power.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    batter_power.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    batter_power.add_argument("--distribution-version", dest="distribution_version", default=None)

    batter_vision = sub.add_parser(
        "calculate-batter-vision",
        help="Inspecciona candidato Vision de batter sin persistir",
    )
    batter_vision.add_argument("--player-id", dest="player_id", type=int, required=True)
    batter_vision.add_argument("--season", type=int, required=True)
    batter_vision.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    batter_vision.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    batter_vision.add_argument("--distribution-version", dest="distribution_version", default=None)

    batter_ratings = sub.add_parser(
        "calculate-batter-ratings",
        help="Ensambla batter ratings-2.0 sin persistir",
    )
    batter_ratings.add_argument("--player-id", dest="player_id", type=int, required=True)
    batter_ratings.add_argument("--season", type=int, required=True)
    batter_ratings.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    batter_ratings.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    batter_ratings.add_argument("--distribution-version", dest="distribution_version", default=None)

    persist_batter_ratings = sub.add_parser(
        "persist-batter-ratings",
        help="Calcula y persiste batter ratings-2.0",
    )
    persist_batter_ratings.add_argument("--player-id", dest="player_id", type=int, required=True)
    persist_batter_ratings.add_argument("--season", type=int, required=True)
    persist_batter_ratings.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    persist_batter_ratings.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    persist_batter_ratings.add_argument(
        "--distribution-version", dest="distribution_version", default=None
    )

    ratings2 = sub.add_parser("calculate-pitcher-ratings2", help="Ensambla ratings-2.0 sin persistir carta")
    ratings2.add_argument("--player-id", dest="player_id", type=int, required=True)
    ratings2.add_argument("--season", type=int, required=True)
    ratings2.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    ratings2.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    ratings2.add_argument("--distribution-version", dest="distribution_version", default=None)

    generate_ratings2 = sub.add_parser("generate-pitcher-ratings2", help="Calcula y persiste pitcher ratings-2.0")
    generate_ratings2.add_argument("--player-id", dest="player_id", type=int, required=True)
    generate_ratings2.add_argument("--season", type=int, required=True)
    generate_ratings2.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    generate_ratings2.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    generate_ratings2.add_argument("--distribution-version", dest="distribution_version", default=None)

    ratings2_population = sub.add_parser(
        "generate-pitcher-ratings2-population",
        help="Calcula y persiste ratings-2.0 para pitchers con Analytics",
    )
    ratings2_population.add_argument("--season", type=int, required=True)
    ratings2_population.add_argument("--from", dest="data_start_date", type=_parse_date, required=True)
    ratings2_population.add_argument("--to", dest="data_end_date", type=_parse_date, required=True)
    ratings2_population.add_argument("--distribution-version", dest="distribution_version", default=None)
    ratings2_population.add_argument("--limit", type=int, default=None)

    batter_ratings_population = sub.add_parser(
        "generate-batter-ratings-population",
        help="Calcula y persiste ratings-2.0 para batters con Analytics",
    )
    batter_ratings_population.add_argument("--season", type=int, required=True)
    batter_ratings_population.add_argument(
        "--from", dest="data_start_date", type=_parse_date, required=True
    )
    batter_ratings_population.add_argument(
        "--to", dest="data_end_date", type=_parse_date, required=True
    )
    batter_ratings_population.add_argument(
        "--distribution-version", dest="distribution_version", default=None
    )
    batter_ratings_population.add_argument("--limit", type=int, default=None)

    ratings_as_of = sub.add_parser(
        "generate-player-ratings-as-of",
        help="Genera Analytics, distribuciones y PlayerRatings season-to-date",
    )
    ratings_as_of.add_argument("--season", type=int, required=True)
    ratings_as_of.add_argument(
        "--role", choices=("batter", "pitcher"), required=True
    )
    ratings_as_of.add_argument(
        "--as-of", dest="as_of_date", type=_parse_date, required=True
    )
    ratings_as_of.add_argument(
        "--distribution-version", dest="distribution_version", default=None
    )
    ratings_as_of.add_argument("--limit", type=int, default=None)

    profile_ratings2 = sub.add_parser("generate-card-profile-ratings2", help="Adapta PlayerRatings a perfil de carta")
    profile_ratings2.add_argument("--player-ratings-id", dest="player_ratings_id", required=True)
    profile_ratings2.add_argument("--player-season-id", dest="player_season_id", default=None)

    walk_off = sub.add_parser(
        "detect-walk-off-hr",
        help="Detecta WALK_OFF_HR confirmado por Statcast + MLB game feed",
    )
    walk_off.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    walk_off.add_argument("--to", dest="date_to", type=_parse_date, required=True)

    multi_hr = sub.add_parser(
        "detect-multi-hr-games",
        help="Detecta juegos de 2+ HR y persiste sus MomentContext",
    )
    multi_hr.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    multi_hr.add_argument("--to", dest="date_to", type=_parse_date, required=True)

    ten_strikeouts = sub.add_parser(
        "detect-ten-strikeout-games",
        help="Detecta juegos de pitcher con 10+ K y persiste sus MomentContext",
    )
    ten_strikeouts.add_argument(
        "--from", dest="date_from", type=_parse_date, required=True
    )
    ten_strikeouts.add_argument(
        "--to", dest="date_to", type=_parse_date, required=True
    )

    sub.add_parser(
        "evaluate-multi-hr-moments",
        help="Evalúa los MomentContext MULTI_HR_GAME descubiertos",
    )
    sub.add_parser(
        "evaluate-ten-strikeout-moments",
        help="Evalúa los MomentContext 10_STRIKEOUT_GAME descubiertos",
    )
    sub.add_parser(
        "generate-multi-hr-moment-card-profiles",
        help="Genera perfiles MOMENT desde evaluaciones MULTI_HR_GAME",
    )
    sub.add_parser(
        "generate-ten-strikeout-moment-card-profiles",
        help="Genera perfiles MOMENT desde evaluaciones 10_STRIKEOUT_GAME",
    )

    walk_off_pipeline = sub.add_parser(
        "run-walk-off-hr-pipeline",
        help="Detecta, evalúa y genera perfiles MOMENT para WALK_OFF_HR",
    )
    walk_off_pipeline.add_argument(
        "--from", dest="date_from", type=_parse_date, required=True
    )
    walk_off_pipeline.add_argument(
        "--to", dest="date_to", type=_parse_date, required=True
    )

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
    pub.add_argument("--card-edition-id", dest="card_edition_id", default=None)
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

        elif args.command == "backfill-statcast":
            result = backfill_statcast(
                db,
                StatcastSourceAdapter(),
                MLBStatsApiClient(),
                season=args.season,
                role=args.role,
                date_to=args.date_to,
                limit=args.limit,
                refresh=args.refresh,
            )
            print(
                f"role={result.role} season={result.season} "
                f"from={result.date_from} to={result.date_to} "
                f"players_selected={result.players_selected} "
                f"players_with_data={result.players_with_data} "
                f"players_without_data={result.players_without_data} "
                f"games={result.games} pitches={result.pitches} "
                f"first_date={result.first_date} last_date={result.last_date} "
                f"created={result.rows_inserted} updated={result.rows_updated} "
                f"unchanged={result.rows_unchanged} "
                f"rejected={result.rows_rejected} "
                f"failed={result.players_failed}"
            )

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

        elif args.command in {"build-rating-distributions", "build-rating-distribution"}:
            result = build_overall_rating_distribution(
                db,
                season=args.season,
                role=args.role,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                rating_model_version=args.rating_model_version,
                source_distribution_version=args.source_distribution_version,
                performance_tier_model_version=args.performance_tier_model_version,
            )
            print(
                f"{result.status} population_size={result.population_size} "
                f"rating_distribution_id={result.rating_distribution_id} "
                f"PERFORMANCE_TIER_MODEL={result.performance_tier_model_version}"
            )

        elif args.command == "calculate-pitcher-movement":
            result = calculate_movement_candidate(
                db, mlb_id=args.player_id, season=args.season,
                data_start_date=args.data_start_date, data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            for pitch in result.pitches:
                print(
                    f"{pitch.pitch_type} scope={pitch.scope} raw={pitch.raw_magnitude:.4f} "
                    f"baseline={pitch.league_baseline:.4f} sample={pitch.pitch_count} "
                    f"weight={pitch.shrinkage_weight:.4f} adjusted={pitch.adjusted_magnitude:.4f} "
                    f"percentile={pitch.percentile:.4f} rating={pitch.rating} usage={pitch.usage:.6f}"
                )
            if result.skipped_pitch_types:
                print(f"skipped={','.join(result.skipped_pitch_types)}")
            print(f"MOVEMENT={result.movement_rating}")

        elif args.command == "calculate-pitcher-control":
            result = calculate_control_candidate(
                db, mlb_id=args.player_id, season=args.season,
                data_start_date=args.data_start_date, data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            for component in result.components:
                print(
                    f"{component.metric} raw={component.observed:.6f} "
                    f"baseline={component.league_baseline:.6f} sample={component.sample_size} "
                    f"stabilization={component.stabilization} weight={component.shrinkage_weight:.4f} "
                    f"adjusted={component.adjusted:.6f} percentile={component.percentile:.4f} "
                    f"rating={component.rating} component_weight={component.component_weight:.2f}"
                )
            if result.skipped_metrics:
                print(f"skipped={','.join(result.skipped_metrics)}")
            print(f"coverage={result.weight_coverage:.2f} CONTROL={result.rating}")

        elif args.command == "calculate-pitcher-velocity":
            result = calculate_velocity_candidate(
                db, mlb_id=args.player_id, season=args.season,
                data_start_date=args.data_start_date, data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            if result.rating is None:
                print(f"avg_velocity unavailable={result.unavailable_reason} VELOCITY=None")
            else:
                print(
                    f"avg_velocity raw={result.observed:.2f} baseline={result.league_baseline:.8f} "
                    f"sample={result.sample_size} stabilization={result.stabilization} "
                    f"weight={result.shrinkage_weight:.4f} adjusted={result.adjusted:.4f} "
                    f"percentile={result.percentile:.4f} VELOCITY={result.rating}"
                )

        elif args.command == "calculate-pitcher-stuff":
            result = calculate_stuff_candidate(
                db, mlb_id=args.player_id, season=args.season,
                data_start_date=args.data_start_date, data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            for component in result.components:
                print(
                    f"{component.metric} raw={component.observed:.6f} "
                    f"baseline={component.league_baseline:.6f} sample={component.sample_size} "
                    f"stabilization={component.stabilization} weight={component.shrinkage_weight:.4f} "
                    f"adjusted={component.adjusted:.6f} percentile={component.percentile:.4f} "
                    f"rating={component.rating} component_weight={component.component_weight:.2f}"
                )
            if result.skipped_metrics:
                print(f"skipped={','.join(result.skipped_metrics)}")
            print(f"coverage={result.weight_coverage:.2f} STUFF={result.rating}")

        elif args.command == "calculate-batter-contact":
            result = calculate_batter_contact(
                db,
                mlb_id=args.player_id,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            for component in result.components:
                print(
                    f"{component.metric} raw={component.observed:.6f} "
                    f"baseline={component.league_baseline:.6f} "
                    f"sample={component.sample_size} "
                    f"stabilization={component.stabilization} "
                    f"weight={component.shrinkage_weight:.4f} "
                    f"adjusted={component.adjusted:.6f} "
                    f"percentile={component.percentile:.4f} rating={component.rating}"
                )
            if result.skipped_metrics:
                print(f"skipped={','.join(result.skipped_metrics)}")
            print(f"CONTACT={result.rating} MODEL={result.rating_model_version}")

        elif args.command == "calculate-batter-power":
            result = calculate_batter_power(
                db,
                mlb_id=args.player_id,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            for component in result.components:
                print(
                    f"{component.metric} raw={component.observed:.6f} "
                    f"baseline={component.league_baseline:.6f} "
                    f"sample={component.sample_size} "
                    f"stabilization={component.stabilization} "
                    f"weight={component.shrinkage_weight:.4f} "
                    f"adjusted={component.adjusted:.6f} "
                    f"percentile={component.percentile:.4f} rating={component.rating}"
                )
            if result.skipped_metrics:
                print(f"skipped={','.join(result.skipped_metrics)}")
            print(f"POWER={result.rating} MODEL={result.rating_model_version}")

        elif args.command == "calculate-batter-vision":
            result = calculate_batter_vision(
                db,
                mlb_id=args.player_id,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            for component in result.components:
                print(
                    f"{component.metric} raw={component.observed:.6f} "
                    f"baseline={component.league_baseline:.6f} "
                    f"sample={component.sample_size} "
                    f"stabilization={component.stabilization} "
                    f"weight={component.shrinkage_weight:.4f} "
                    f"adjusted={component.adjusted:.6f} "
                    f"percentile={component.percentile:.4f} rating={component.rating}"
                )
            if result.skipped_metrics:
                print(f"skipped={','.join(result.skipped_metrics)}")
            print(f"VISION={result.rating} MODEL={result.rating_model_version}")

        elif args.command == "calculate-batter-ratings":
            result = calculate_batter_ratings2(
                db,
                mlb_id=args.player_id,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            print(
                f"CONTACT={result.contact.rating} POWER={result.power.rating} "
                f"VISION={result.vision.rating} CLUTCH={result.clutch.rating} "
                f"OVERALL={result.overall_rating} MODEL={result.model_version}"
            )
            if result.skipped_components:
                print(f"skipped={','.join(result.skipped_components)}")

        elif args.command == "persist-batter-ratings":
            ratings = calculate_batter_ratings2(
                db,
                mlb_id=args.player_id,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            persisted = persist_batter_ratings2(
                db,
                ratings,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
            )
            print(
                f"{persisted.status} player_ratings_id={persisted.player_ratings_id}"
            )
            print(
                f"CONTACT={ratings.contact.rating} POWER={ratings.power.rating} "
                f"VISION={ratings.vision.rating} CLUTCH={ratings.clutch.rating} "
                f"OVERALL={ratings.overall_rating} MODEL={ratings.model_version}"
            )
            if persisted.skipped_components:
                print(f"skipped={','.join(persisted.skipped_components)}")

        elif args.command == "calculate-pitcher-ratings2":
            result = calculate_pitcher_ratings2(
                db, mlb_id=args.player_id, season=args.season,
                data_start_date=args.data_start_date, data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            print(f"VELOCITY={result.velocity.rating}")
            print(f"CONTROL={result.control.rating}")
            print(f"MOVEMENT={result.movement.rating}")
            print(f"STUFF={result.stuff.rating}")
            print(f"OVERALL={result.overall}")
            print(f"MODEL={result.rating_model_version}")
            if result.unavailable_attributes:
                print(f"unavailable={','.join(result.unavailable_attributes)}")

        elif args.command == "generate-pitcher-ratings2":
            ratings = calculate_pitcher_ratings2(
                db, mlb_id=args.player_id, season=args.season,
                data_start_date=args.data_start_date, data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
            )
            persisted = persist_pitcher_ratings2(
                db, ratings, season=args.season,
                data_start_date=args.data_start_date, data_end_date=args.data_end_date,
            )
            print(persisted.status)
            print(
                f"VELOCITY={ratings.velocity.rating} CONTROL={ratings.control.rating} "
                f"MOVEMENT={ratings.movement.rating} STUFF={ratings.stuff.rating} "
                f"OVERALL={ratings.overall} MODEL={ratings.rating_model_version}"
            )

        elif args.command == "generate-pitcher-ratings2-population":
            result = generate_pitcher_ratings2_population(
                db,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
                limit=args.limit,
            )
            print(
                f"selected={result.selected} completed={result.completed} "
                f"created={result.created} updated={result.updated} "
                f"unchanged={result.unchanged} "
                f"skipped_incomplete={result.skipped_incomplete} failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "pitcher ratings-2.0 failed mlb_id=%s error=%s",
                    failure.mlb_id,
                    failure.error,
                )

        elif args.command == "generate-batter-ratings-population":
            result = generate_batter_ratings2_population(
                db,
                season=args.season,
                data_start_date=args.data_start_date,
                data_end_date=args.data_end_date,
                distribution_version=args.distribution_version,
                limit=args.limit,
            )
            print(
                f"selected={result.selected} completed={result.completed} "
                f"created={result.created} updated={result.updated} "
                f"unchanged={result.unchanged} "
                f"skipped_incomplete={result.skipped_incomplete} failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "batter ratings-2.0 failed mlb_id=%s error=%s",
                    failure.mlb_id,
                    failure.error,
                )

        elif args.command == "generate-card-profile-ratings2":
            result = generate_card_profile_from_ratings2(
                db,
                player_ratings_id=args.player_ratings_id,
                player_season_id=args.player_season_id,
            )
            print(
                f"{result.status} card_generation_profile_id={result.card_generation_profile_id} "
                f"player_ratings_id={result.player_ratings_id}"
            )

        elif args.command == "generate-player-ratings-as-of":
            result = generate_player_ratings_as_of(
                db,
                season=args.season,
                role=args.role,
                as_of_date=args.as_of_date,
                distribution_version=args.distribution_version,
                limit=args.limit,
            )
            print(
                f"role={result.role} season={result.season} "
                f"from={result.data_start_date} as_of={result.data_end_date} "
                f"analytics_players={result.analytics.players_processed} "
                f"distributions_created={result.distributions.created} "
                f"distributions_updated={result.distributions.updated} "
                f"distributions_unchanged={result.distributions.unchanged} "
                f"selected={result.ratings.selected} "
                f"completed={result.ratings.completed} "
                f"created={result.ratings.created} "
                f"updated={result.ratings.updated} "
                f"unchanged={result.ratings.unchanged} "
                f"skipped_incomplete={result.ratings.skipped_incomplete} "
                f"failed={result.ratings.failed}"
            )

        elif args.command == "detect-walk-off-hr":
            result = detect_walk_off_home_runs(
                db,
                MLBStatsApiClient(),
                date_from=args.date_from,
                date_to=args.date_to,
            )
            print(
                f"selected={result.selected} confirmed={result.confirmed} "
                f"created={result.created} updated={result.updated} "
                f"unchanged={result.unchanged} unconfirmed={result.unconfirmed} "
                f"failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "walk-off detector game_pk=%s at_bat=%s batter=%s reason=%s",
                    failure.game_pk,
                    failure.at_bat_number,
                    failure.batter_mlb_id,
                    failure.reason,
                )

        elif args.command == "detect-multi-hr-games":
            result = detect_multi_hr_games(
                db,
                MLBStatsApiClient(),
                date_from=args.date_from,
                date_to=args.date_to,
            )
            print(
                f"selected={result.selected} confirmed={result.confirmed} "
                f"created={result.created} updated={result.updated} "
                f"unchanged={result.unchanged} unconfirmed={result.unconfirmed} "
                f"failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "multi-HR detector game_pk=%s batter=%s reason=%s",
                    failure.game_pk,
                    failure.batter_mlb_id,
                    failure.reason,
                )

        elif args.command == "detect-ten-strikeout-games":
            result = detect_ten_strikeout_games(
                db,
                MLBStatsApiClient(),
                date_from=args.date_from,
                date_to=args.date_to,
            )
            print(
                f"selected={result.selected} confirmed={result.confirmed} "
                f"created={result.created} updated={result.updated} "
                f"unchanged={result.unchanged} unconfirmed={result.unconfirmed} "
                f"failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "10-K detector game_pk=%s pitcher=%s reason=%s",
                    failure.game_pk,
                    failure.pitcher_mlb_id,
                    failure.reason,
                )

        elif args.command == "evaluate-multi-hr-moments":
            result = evaluate_discovered_multi_hr_moments(db)
            print(
                f"selected={result.selected} created={result.created} "
                f"updated={result.updated} unchanged={result.unchanged} "
                f"failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "multi-HR evaluation context=%s reason=%s",
                    failure.moment_context_id,
                    failure.reason,
                )

        elif args.command == "evaluate-ten-strikeout-moments":
            result = evaluate_discovered_ten_strikeout_moments(db)
            print(
                f"selected={result.selected} created={result.created} "
                f"updated={result.updated} unchanged={result.unchanged} "
                f"failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "10-K evaluation context=%s reason=%s",
                    failure.moment_context_id,
                    failure.reason,
                )

        elif args.command == "generate-multi-hr-moment-card-profiles":
            result = generate_multi_hr_moment_card_profiles(db)
            print(
                f"selected={result.selected} created={result.created} "
                f"updated={result.updated} unchanged={result.unchanged} "
                f"skipped_no_ratings={result.skipped_no_ratings} "
                f"failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "multi-HR profile evaluation=%s reason=%s",
                    failure.moment_evaluation_id,
                    failure.reason,
                )

        elif args.command == "generate-ten-strikeout-moment-card-profiles":
            result = generate_ten_strikeout_moment_card_profiles(db)
            print(
                f"selected={result.selected} created={result.created} "
                f"updated={result.updated} unchanged={result.unchanged} "
                f"skipped_no_ratings={result.skipped_no_ratings} "
                f"failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "10-K profile evaluation=%s reason=%s",
                    failure.moment_evaluation_id,
                    failure.reason,
                )

        elif args.command == "run-walk-off-hr-pipeline":
            result = run_walk_off_hr_pipeline(
                db,
                MLBStatsApiClient(),
                date_from=args.date_from,
                date_to=args.date_to,
            )
            print(
                f"candidates={result.candidates} confirmed={result.confirmed} "
                f"unconfirmed={result.unconfirmed} "
                f"contexts_created={result.contexts_created} "
                f"contexts_updated={result.contexts_updated} "
                f"contexts_unchanged={result.contexts_unchanged} "
                f"evaluated={result.evaluated} "
                f"evaluations_created={result.evaluations_created} "
                f"evaluations_updated={result.evaluations_updated} "
                f"evaluations_unchanged={result.evaluations_unchanged} "
                f"profiles_created={result.profiles_created} "
                f"profiles_updated={result.profiles_updated} "
                f"profiles_unchanged={result.profiles_unchanged} "
                f"profiles_skipped_no_ratings="
                f"{result.profiles_skipped_no_ratings} "
                f"failed={result.failed}"
            )
            for failure in result.failures:
                logger.warning(
                    "walk-off pipeline stage=%s context=%s reason=%s",
                    failure.stage,
                    failure.moment_context_id,
                    failure.reason,
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
            card_edition_id = args.card_edition_id
            if card_edition_id is None:
                if args.edition != "BASE":
                    raise ValueError(
                        "--card-edition-id es obligatorio para ediciones no BASE"
                    )
                card_edition_id = ensure_system_base_edition(
                    db, season=args.season
                ).id
            result = publish_card_catalog(
                db, season=args.season,
                card_edition_id=card_edition_id,
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
