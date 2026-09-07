"""Backfill histórico Statcast por población y con cobertura observable."""

import datetime as dt

import pytest

from app.models import Player
from etl.cli import _build_parser
from etl.services.statcast_backfill import (
    backfill_statcast,
    resolve_regular_season_start,
)
from etl.services.statcast_population import PopulationImportResult


DATE_TO = dt.date(2026, 8, 24)
OPENING_DAY = dt.date(2026, 3, 25)


class FakeMLBClient:
    def __init__(self, schedule):
        self.schedule = schedule
        self.calls = []

    def get_schedule(self, date_from, date_to, *, game_type=None):
        self.calls.append((date_from, date_to, game_type))
        return self.schedule


def _schedule():
    return {
        "dates": [
            {
                "date": "2026-03-27",
                "games": [{"gamePk": 2, "gameType": "R"}],
            },
            {
                "date": OPENING_DAY.isoformat(),
                "games": [{"gamePk": 1, "gameType": "R"}],
            },
        ]
    }


def test_resuelve_primer_juego_regular_desde_schedule():
    client = FakeMLBClient(_schedule())
    assert resolve_regular_season_start(
        client, season=2026, date_to=DATE_TO
    ) == OPENING_DAY
    assert client.calls == [(dt.date(2026, 1, 1), DATE_TO, "R")]


def test_rechaza_temporada_sin_juegos_regulares():
    client = FakeMLBClient({"dates": []})
    with pytest.raises(ValueError, match="no contiene juegos regulares"):
        resolve_regular_season_start(client, season=2026, date_to=DATE_TO)


def test_orquesta_poblacion_y_reporta_cobertura(monkeypatch):
    players = [Player(mlb_id=814439), Player(mlb_id=660271)]
    calls = []
    imported = PopulationImportResult(
        players_selected=2,
        players_completed=1,
        players_no_data=1,
        rows_extracted=120,
        rows_inserted=100,
        rows_unchanged=20,
    )
    monkeypatch.setattr(
        "etl.services.statcast_backfill.resolve_regular_season_start",
        lambda *_args, **_kwargs: OPENING_DAY,
    )
    monkeypatch.setattr(
        "etl.services.statcast_backfill.select_population_players",
        lambda *_args, **_kwargs: players,
    )

    def importer(db, adapter, **kwargs):
        calls.append(kwargs)
        return imported

    monkeypatch.setattr(
        "etl.services.statcast_backfill.import_statcast_population", importer
    )
    monkeypatch.setattr(
        "etl.services.statcast_backfill._coverage",
        lambda *_args, **_kwargs: (
            120,
            8,
            OPENING_DAY,
            DATE_TO,
            1,
        ),
    )

    result = backfill_statcast(
        object(),
        object(),
        object(),
        season=2026,
        role="batter",
        date_to=DATE_TO,
    )

    assert calls == [
        {
            "season": 2026,
            "role": "batter",
            "date_from": OPENING_DAY,
            "date_to": DATE_TO,
            "limit": None,
            "refresh": False,
        }
    ]
    assert result.players_selected == 2
    assert result.players_with_data == 1
    assert result.players_without_data == 1
    assert (result.games, result.pitches) == (8, 120)
    assert (result.first_date, result.last_date) == (OPENING_DAY, DATE_TO)
    assert (result.rows_inserted, result.rows_unchanged) == (100, 20)


def test_rerun_expone_filas_unchanged_sin_created(monkeypatch):
    player = Player(mlb_id=814439)
    outcomes = iter(
        (
            PopulationImportResult(rows_inserted=100),
            PopulationImportResult(rows_unchanged=100),
        )
    )
    monkeypatch.setattr(
        "etl.services.statcast_backfill.resolve_regular_season_start",
        lambda *_args, **_kwargs: OPENING_DAY,
    )
    monkeypatch.setattr(
        "etl.services.statcast_backfill.select_population_players",
        lambda *_args, **_kwargs: [player],
    )
    monkeypatch.setattr(
        "etl.services.statcast_backfill.import_statcast_population",
        lambda *_args, **_kwargs: next(outcomes),
    )
    monkeypatch.setattr(
        "etl.services.statcast_backfill._coverage",
        lambda *_args, **_kwargs: (100, 5, OPENING_DAY, DATE_TO, 1),
    )

    first = backfill_statcast(
        object(), object(), object(), season=2026, role="batter", date_to=DATE_TO
    )
    second = backfill_statcast(
        object(), object(), object(), season=2026, role="batter", date_to=DATE_TO
    )
    assert (first.rows_inserted, first.rows_unchanged) == (100, 0)
    assert (second.rows_inserted, second.rows_unchanged) == (0, 100)


def test_cli_no_exige_from_ni_limit():
    args = _build_parser().parse_args(
        [
            "backfill-statcast",
            "--season",
            "2026",
            "--role",
            "batter",
            "--to",
            "2026-08-24",
        ]
    )
    assert args.date_to == DATE_TO
    assert args.limit is None
