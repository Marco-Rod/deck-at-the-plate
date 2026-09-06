"""Prueba del parser CLI (spec §35) sin ejecutar red."""

from etl.cli import _build_parser


def test_parser_generates_subcomandos():
    parser = _build_parser()
    commands = {
        "sync-teams": ["sync-teams", "--season", "2026"],
        "sync-rosters": ["sync-rosters", "--season", "2026", "--start", "2026-03-20", "--end", "2026-08-31"],
        "import-statcast": ["import-statcast", "--from", "2026-04-01", "--to", "2026-04-05"],
        "import-statcast-player": ["import-statcast-player", "--player-id", "660271", "--from", "2026-04-01", "--to", "2026-04-05"],
        "build-analytics": ["build-analytics", "--season", "2026", "--data-start-date", "2026-03-20", "--data-end-date", "2026-08-31"],
        "run": ["run", "--season", "2026", "--from", "2026-04-01", "--to", "2026-04-05"],
        "generate-profiles": ["generate-profiles", "--season", "2026"],
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


def test_build_analytics_fechas():
    parser = _build_parser()
    args = parser.parse_args(["build-analytics", "--season", "2026", "--data-start-date", "2026-03-20", "--data-end-date", "2026-08-31"])
    assert args.season == 2026
    assert args.data_start_date.isoformat() == "2026-03-20"


def test_generate_profiles_requiere_season():
    parser = _build_parser()
    args = parser.parse_args(["generate-profiles", "--season", "2026"])
    assert args.command == "generate-profiles"