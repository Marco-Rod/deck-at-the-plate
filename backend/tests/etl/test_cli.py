"""Prueba del parser CLI (spec §35) sin ejecutar red."""

from etl.cli import _build_parser
from etl.config import RATING_MODEL_VERSION


def test_parser_generates_subcomandos():
    parser = _build_parser()
    commands = {
        "sync-source-teams": ["sync-source-teams", "--season", "2026"],
        "sync-game-team-mappings": ["sync-game-team-mappings", "--season", "2026"],
        "generate-game-identities": ["generate-game-identities"],
        "sync-rosters": ["sync-rosters", "--season", "2026", "--start", "2026-03-20", "--end", "2026-08-31"],
        "import-statcast": ["import-statcast", "--from", "2026-04-01", "--to", "2026-04-05"],
        "import-statcast-player": ["import-statcast-player", "--player-id", "660271", "--from", "2026-04-01", "--to", "2026-04-05"],
        "import-statcast-population": ["import-statcast-population", "--season", "2026", "--role", "pitcher", "--from", "2026-04-01", "--to", "2026-04-05", "--limit", "40"],
        "build-analytics": ["build-analytics", "--season", "2026", "--data-start-date", "2026-03-20", "--data-end-date", "2026-08-31"],
        "build-league-distributions": ["build-league-distributions", "--season", "2026", "--role", "pitcher", "--from", "2026-03-20", "--to", "2026-08-31"],
        "calculate-pitcher-movement": ["calculate-pitcher-movement", "--player-id", "650911", "--season", "2026", "--from", "2026-03-20", "--to", "2026-08-31"],
        "calculate-pitcher-control": ["calculate-pitcher-control", "--player-id", "650911", "--season", "2026", "--from", "2026-03-20", "--to", "2026-08-31"],
        "calculate-pitcher-velocity": ["calculate-pitcher-velocity", "--player-id", "650911", "--season", "2026", "--from", "2026-03-20", "--to", "2026-08-31"],
        "run": ["run", "--season", "2026", "--from", "2026-04-01", "--to", "2026-04-05"],
        "generate-card-profiles": ["generate-card-profiles", "--season", "2026"],
        "validate-card-profiles": ["validate-card-profiles", "--season", "2026"],
        "publish-card-catalog": ["publish-card-catalog", "--season", "2026"],
        "validate-cpu-rosters": ["validate-cpu-rosters", "--season", "2026"],
        "validate-pack-pool": ["validate-pack-pool", "--season", "2026"],
    }
    for cmd in commands:
        args = parser.parse_args(commands[cmd])
        assert args.command == cmd


def test_sync_rosters_fechas():
    parser = _build_parser()
    args = parser.parse_args(["sync-rosters", "--season", "2026", "--start", "2026-03-20", "--end", "2026-08-31"])
    assert args.command == "sync-rosters"
    assert args.start.isoformat() == "2026-03-20"
    assert args.end.isoformat() == "2026-08-31"


def test_import_statcast_flags():
    parser = _build_parser()
    args = parser.parse_args(["import-statcast", "--from", "2026-04-01", "--to", "2026-04-05", "--refresh"])
    assert args.date_from.isoformat() == "2026-04-01"
    assert args.date_to.isoformat() == "2026-04-05"
    assert args.refresh is True


def test_import_statcast_population_flags():
    parser = _build_parser()
    args = parser.parse_args([
        "import-statcast-population", "--season", "2026", "--role", "pitcher",
        "--from", "2026-08-25", "--to", "2026-09-02", "--limit", "35", "--refresh",
    ])
    assert args.season == 2026
    assert args.role == "pitcher"
    assert args.limit == 35
    assert args.refresh is True


def test_build_analytics_fechas():
    parser = _build_parser()
    args = parser.parse_args(["build-analytics", "--season", "2026", "--data-start-date", "2026-03-20", "--data-end-date", "2026-08-31"])
    assert args.season == 2026
    assert args.data_start_date.isoformat() == "2026-03-20"


def test_build_league_distributions_flags():
    parser = _build_parser()
    args = parser.parse_args([
        "build-league-distributions", "--season", "2026", "--role", "pitcher",
        "--from", "2026-08-25", "--to", "2026-09-02",
        "--distribution-version", "mlb-2026-test",
    ])
    assert args.data_start_date.isoformat() == "2026-08-25"
    assert args.data_end_date.isoformat() == "2026-09-02"
    assert args.distribution_version == "mlb-2026-test"


def test_generate_card_profiles_flags():
    parser = _build_parser()
    args = parser.parse_args(
        ["generate-card-profiles", "--season", "2026", "--data-end-date", "2026-08-31", "--rating-model", "v2"]
    )
    assert args.command == "generate-card-profiles"
    assert args.data_end_date.isoformat() == "2026-08-31"
    assert args.rating_model == "v2"


def test_card_profile_commands_usan_rating_model_configurado_por_default():
    parser = _build_parser()
    for command in (
        "generate-card-profiles",
        "validate-card-profiles",
        "publish-card-catalog",
    ):
        args = parser.parse_args([command, "--season", "2026"])
        assert args.rating_model == RATING_MODEL_VERSION


def test_generate_game_identities_all():
    parser = _build_parser()
    args = parser.parse_args(["generate-game-identities", "--season", "2026", "--all"])
    assert args.season == 2026
    assert args.all is True


def test_generate_game_identities_v21_flags():
    parser = _build_parser()
    args = parser.parse_args(
        [
            "generate-game-identities",
            "--season", "2026",
            "--missing-only",
            "--generator-version", "names-1.0",
            "--dry-run",
            "--player-id", "660271",
            "--limit", "5",
            "--report",
        ]
    )
    assert args.command == "generate-game-identities"
    assert args.missing_only is True
    assert args.generator_version == "names-1.0"
    assert args.dry_run is True
    assert args.player_id == 660271
    assert args.limit == 5
    assert args.report is True


def test_validate_game_identities_flag():
    parser = _build_parser()
    args = parser.parse_args(["validate-game-identities", "--season", "2026"])
    assert args.command == "validate-game-identities"
    assert args.season == 2026


def test_publish_card_catalog_edition():
    parser = _build_parser()
    args = parser.parse_args(["publish-card-catalog", "--season", "2026", "--edition", "BASE"])
    assert args.command == "publish-card-catalog"
    assert args.edition == "BASE"
