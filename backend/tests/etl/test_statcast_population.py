"""Pruebas del orquestador de importación Statcast por población."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, PlayerSeason
from etl.pipelines.statcast import StatcastRunResult
from etl.services.statcast_population import import_statcast_population, select_population_players


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _player(db, mlb_id: int, position: str, season: int = 2026):
    player = Player(mlb_id=mlb_id, full_name=f"Player {mlb_id}", primary_position=position)
    db.add(player)
    db.flush()
    db.add(PlayerSeason(
        player_id=player.id,
        season=season,
        data_start_date=START,
        data_end_date=END,
    ))
    return player


def test_seleccion_es_de_pitchers_determinista_y_limitada(db):
    _player(db, 30, "RP")
    _player(db, 10, "SP")
    _player(db, 20, "TWP")
    _player(db, 5, "SS")
    _player(db, 1, "SP", season=2025)
    db.commit()
    selected = select_population_players(db, season=2026, role="pitcher", limit=2)
    assert [player.mlb_id for player in selected] == [10, 20]


def test_seleccion_batter_excluye_pitchers_puros_e_incluye_twp(db):
    _player(db, 30, "DH")
    _player(db, 10, "SP")
    _player(db, 20, "TWP")
    _player(db, 5, "SS")
    _player(db, 40, "RP")
    _player(db, 1, "CF", season=2025)
    db.commit()

    selected = select_population_players(db, season=2026, role="batter", limit=40)

    assert [player.mlb_id for player in selected] == [5, 20, 30]


def test_seleccion_sin_limit_devuelve_toda_la_poblacion(db):
    for mlb_id in (30, 10, 20):
        _player(db, mlb_id, "DH")
    db.commit()

    selected = select_population_players(
        db, season=2026, role="batter", limit=None
    )

    assert [player.mlb_id for player in selected] == [10, 20, 30]


def test_importacion_batter_propaga_role_y_conserva_contadores(db):
    _player(db, 10, "TWP")
    _player(db, 20, "DH")
    _player(db, 30, "SP")
    db.commit()
    calls = []

    class FakeBatterPipeline:
        def __init__(self, _db, _adapter):
            pass

        def run_player(self, *, mlb_id, role, **_kwargs):
            calls.append((mlb_id, role))
            return StatcastRunResult(rows_extracted=5, rows_inserted=5)

    result = import_statcast_population(
        db,
        object(),
        season=2026,
        role="batter",
        date_from=START,
        date_to=END,
        limit=40,
        pipeline_factory=FakeBatterPipeline,
    )

    assert calls == [(10, "batter"), (20, "batter")]
    assert result.players_selected == 2
    assert result.players_completed == 2
    assert result.rows_inserted == 10


def test_importacion_aisla_fallos_y_agrega_resultados(db):
    for mlb_id in (10, 20, 30):
        _player(db, mlb_id, "SP")
    db.commit()

    class FakePipeline:
        def __init__(self, _db, _adapter):
            pass

        def run_player(self, *, mlb_id, **_kwargs):
            if mlb_id == 20:
                raise TimeoutError("timeout de prueba")
            if mlb_id == 30:
                return StatcastRunResult()
            return StatcastRunResult(
                rows_extracted=10,
                rows_inserted=7,
                rows_updated=1,
                rows_unchanged=2,
                rows_rejected=1,
            )

    result = import_statcast_population(
        db, object(), season=2026, role="pitcher", date_from=START, date_to=END,
        limit=40, pipeline_factory=FakePipeline,
    )
    assert result.players_selected == 3
    assert result.players_completed == 1
    assert result.players_no_data == 1
    assert result.players_failed == 1
    assert result.rows_extracted == 10
    assert result.rows_inserted == 7
    assert result.rows_updated == 1
    assert result.rows_unchanged == 2
    assert result.rows_rejected == 1
    assert result.failures[0].mlb_id == 20


def test_segunda_ejecucion_reporta_raw_sin_cambios(db):
    _player(db, 10, "SP")
    db.commit()
    calls = 0

    class IdempotentPipeline:
        def __init__(self, _db, _adapter):
            pass

        def run_player(self, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return StatcastRunResult(rows_extracted=8, rows_inserted=8)
            return StatcastRunResult(rows_extracted=8, rows_unchanged=8)

    first = import_statcast_population(
        db, object(), season=2026, role="pitcher", date_from=START, date_to=END,
        limit=1, pipeline_factory=IdempotentPipeline,
    )
    second = import_statcast_population(
        db, object(), season=2026, role="pitcher", date_from=START, date_to=END,
        limit=1, pipeline_factory=IdempotentPipeline,
    )
    assert first.rows_inserted == 8
    assert second.rows_inserted == 0
    assert second.rows_unchanged == 8
