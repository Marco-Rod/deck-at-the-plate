"""Orquestación season-to-date de PlayerRatings históricos."""

import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from etl.cli import _build_parser
from etl.services.player_ratings_as_of import generate_player_ratings_as_of


AS_OF = dt.date(2026, 8, 24)
SEASON_START = dt.date(2026, 3, 25)


def _install_fakes(monkeypatch):
    calls = []
    analytics_result = SimpleNamespace(players_processed=225, profiles_created=900)
    distribution_result = SimpleNamespace(
        created=10, updated=0, unchanged=0, skipped=0, version="dist-1.0"
    )
    ratings_result = SimpleNamespace(
        selected=225,
        completed=200,
        created=200,
        updated=0,
        unchanged=0,
        skipped_incomplete=25,
        failed=0,
    )

    class FakeAnalyticsPipeline:
        def __init__(self, db):
            calls.append(("analytics_init", db))

        def rebuild(self, **kwargs):
            calls.append(("analytics", kwargs))
            return analytics_result

    def distributions(db, **kwargs):
        calls.append(("distributions", db, kwargs))
        return distribution_result

    def batter(db, **kwargs):
        calls.append(("batter", db, kwargs))
        return ratings_result

    def pitcher(db, **kwargs):
        calls.append(("pitcher", db, kwargs))
        return ratings_result

    monkeypatch.setattr(
        "etl.services.player_ratings_as_of.resolve_regular_season_start",
        lambda *_args, **_kwargs: SEASON_START,
    )
    monkeypatch.setattr(
        "etl.services.player_ratings_as_of._require_raw_data",
        lambda *_args, **_kwargs: calls.append(("raw_guard", _kwargs)),
    )
    monkeypatch.setattr(
        "etl.services.player_ratings_as_of.AnalyticsPipeline",
        FakeAnalyticsPipeline,
    )
    monkeypatch.setattr(
        "etl.services.player_ratings_as_of.build_league_distributions",
        distributions,
    )
    monkeypatch.setattr(
        "etl.services.player_ratings_as_of.generate_batter_ratings2_population",
        batter,
    )
    monkeypatch.setattr(
        "etl.services.player_ratings_as_of.generate_pitcher_ratings2_population",
        pitcher,
    )
    return calls


def test_batter_as_of_reutiliza_las_tres_capas_con_ventana_season_to_date(monkeypatch):
    calls = _install_fakes(monkeypatch)
    db = object()

    result = generate_player_ratings_as_of(
        db,
        season=2026,
        role="batter",
        as_of_date=AS_OF,
        distribution_version="dist-1.0",
        limit=40,
    )

    assert (result.role, result.data_start_date, result.data_end_date) == (
        "BATTER",
        SEASON_START,
        AS_OF,
    )
    assert [call[0] for call in calls] == [
        "raw_guard",
        "analytics_init",
        "analytics",
        "distributions",
        "batter",
    ]
    for call in (calls[2], calls[3], calls[4]):
        kwargs = call[-1]
        assert kwargs["season"] == 2026
        assert kwargs["data_start_date"] == SEASON_START
        assert kwargs["data_end_date"] == AS_OF
    assert calls[4][-1]["limit"] == 40


def test_pitcher_as_of_usa_population_pitcher(monkeypatch):
    calls = _install_fakes(monkeypatch)
    generate_player_ratings_as_of(
        object(), season=2026, role="PITCHER", as_of_date=AS_OF
    )
    assert calls[-1][0] == "pitcher"
    assert calls[3][-1]["role"] == "PITCHER"


@pytest.mark.parametrize(
    ("role", "as_of_date", "limit"),
    (("catcher", AS_OF, None), ("batter", dt.date(2025, 8, 24), None), ("batter", AS_OF, 0)),
)
def test_rechaza_parametros_invalidos(role, as_of_date, limit):
    with pytest.raises(ValueError):
        generate_player_ratings_as_of(
            object(),
            season=2026,
            role=role,
            as_of_date=as_of_date,
            limit=limit,
        )


def test_cli_expone_as_of_sin_exigir_from_to():
    args = _build_parser().parse_args(
        [
            "generate-player-ratings-as-of",
            "--season",
            "2026",
            "--role",
            "batter",
            "--as-of",
            "2026-08-24",
        ]
    )
    assert args.as_of_date == AS_OF


def test_no_genera_snapshot_vacio_si_falta_raw():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        with pytest.raises(ValueError, match="sin RawPitchEvent"):
            generate_player_ratings_as_of(
                db,
                season=2026,
                role="batter",
                as_of_date=AS_OF,
                mlb_client=SimpleNamespace(
                    get_schedule=lambda *_args, **_kwargs: {
                        "dates": [
                            {
                                "date": SEASON_START.isoformat(),
                                "games": [{"gameType": "R"}],
                            }
                        ]
                    }
                ),
            )
    finally:
        db.close()
        engine.dispose()
