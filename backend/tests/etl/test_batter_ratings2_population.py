"""Pruebas del batch tolerante a fallos de batter ratings-2.0."""

import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import BatterSeasonStats, Player, PlayerSeason
from etl.services.batter_ratings2_population import (
    generate_batter_ratings2_population,
    select_batter_ratings2_population,
)


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    positions = {101: "DH", 102: "RF", 103: "1B", 104: "TWP", 105: "C"}
    for mlb_id, position in positions.items():
        player = Player(
            mlb_id=mlb_id,
            full_name=f"Batter {mlb_id}",
            primary_position=position,
        )
        session.add(player)
        session.flush()
        snapshot = PlayerSeason(
            player_id=player.id,
            season=2026,
            data_start_date=START,
            data_end_date=END,
        )
        session.add(snapshot)
        session.flush()
        session.add(BatterSeasonStats(player_season_id=snapshot.id))

    # Snapshot sin Analytics: no es candidato.
    no_analytics = Player(mlb_id=106, full_name="No Analytics", primary_position="SS")
    session.add(no_analytics)
    session.flush()
    session.add(PlayerSeason(
        player_id=no_analytics.id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    ))

    # Analytics de otra ventana: tampoco es candidato.
    other_window = Player(mlb_id=107, full_name="Other Window", primary_position="LF")
    session.add(other_window)
    session.flush()
    snapshot = PlayerSeason(
        player_id=other_window.id,
        season=2026,
        data_start_date=START,
        data_end_date=dt.date(2026, 9, 1),
    )
    session.add(snapshot)
    session.flush()
    session.add(BatterSeasonStats(player_season_id=snapshot.id))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _component(rating):
    return SimpleNamespace(rating=rating, distribution_version="dist-1.0")


def _calculator(_db, *, mlb_id, **_kwargs):
    if mlb_id == 103:
        raise RuntimeError("unexpected calculator failure")
    rating = None if mlb_id == 102 else 70
    return SimpleNamespace(
        mlb_id=mlb_id,
        contact=_component(rating),
        power=_component(rating),
        vision=_component(rating),
        clutch=_component(rating),
        overall_rating=rating,
    )


def test_contadores_aislamiento_y_segunda_corrida_unchanged(db):
    calls: dict[int, int] = {}

    def persister(_db, ratings, **_kwargs):
        count = calls.get(ratings.mlb_id, 0)
        calls[ratings.mlb_id] = count + 1
        if count:
            status = "UNCHANGED"
        else:
            status = {101: "CREATED", 104: "UPDATED", 105: "UNCHANGED"}[
                ratings.mlb_id
            ]
        return SimpleNamespace(status=status)

    first = generate_batter_ratings2_population(
        db,
        season=2026,
        data_start_date=START,
        data_end_date=END,
        calculator=_calculator,
        persister=persister,
    )
    assert (first.selected, first.completed) == (5, 3)
    assert (first.created, first.updated, first.unchanged) == (1, 1, 1)
    assert (first.skipped_incomplete, first.failed) == (1, 1)
    assert first.failures[0].mlb_id == 103

    second = generate_batter_ratings2_population(
        db,
        season=2026,
        data_start_date=START,
        data_end_date=END,
        calculator=_calculator,
        persister=persister,
    )
    assert (second.selected, second.completed) == (5, 3)
    assert (second.created, second.updated, second.unchanged) == (0, 0, 3)
    assert (second.skipped_incomplete, second.failed) == (1, 1)


def test_selector_es_determinista_snapshot_exacto_incluye_twp_y_limit(db):
    selected = select_batter_ratings2_population(
        db, season=2026, data_start_date=START, data_end_date=END
    )
    assert [row.mlb_id for row in selected] == [101, 102, 103, 104, 105]
    assert any(row.primary_position == "TWP" for row in selected)
    assert [row.mlb_id for row in select_batter_ratings2_population(
        db,
        season=2026,
        data_start_date=START,
        data_end_date=END,
        limit=2,
    )] == [101, 102]


def test_selector_valida_ventana_y_limit(db):
    with pytest.raises(ValueError, match="mayor que cero"):
        select_batter_ratings2_population(
            db,
            season=2026,
            data_start_date=START,
            data_end_date=END,
            limit=0,
        )
    with pytest.raises(ValueError, match="posterior"):
        select_batter_ratings2_population(
            db,
            season=2026,
            data_start_date=END,
            data_end_date=START,
        )
