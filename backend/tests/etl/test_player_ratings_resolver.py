"""Resolución temporal de PlayerRatings para contenido basado en eventos."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, PlayerRatings
from etl.services.player_ratings_resolver import resolve_player_ratings_as_of


EVENT_DATE = dt.date(2026, 8, 25)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _ratings(db, player, *, start, end, model="ratings-2.0", dist="dist-1.0"):
    row = PlayerRatings(
        player_id=player.id,
        season=2026,
        role="BATTER",
        rating_model_version=model,
        distribution_version=dist,
        data_start_date=start,
        data_end_date=end,
        contact_rating=70,
        power_rating=70,
        vision_rating=70,
        clutch_rating=70,
        overall_rating=70,
        input_hash=(str(end.day)[-1] * 64),
    )
    db.add(row)
    db.flush()
    return row


def _resolve(db, player):
    return resolve_player_ratings_as_of(
        db,
        player_id=player.id,
        role="BATTER",
        season=2026,
        as_of_date=EVENT_DATE,
        rating_model_version="ratings-2.0",
        distribution_version="dist-1.0",
    )


def test_elige_snapshot_anterior_mas_cercano(db):
    player = Player(mlb_id=814439, full_name="Ryan Waldschmidt")
    db.add(player)
    db.flush()
    _ratings(db, player, start=dt.date(2026, 7, 1), end=dt.date(2026, 8, 10))
    expected = _ratings(
        db, player, start=dt.date(2026, 8, 1), end=dt.date(2026, 8, 24)
    )

    assert _resolve(db, player).id == expected.id


def test_rechaza_snapshot_del_mismo_dia_y_futuro(db):
    player = Player(mlb_id=814439, full_name="Ryan Waldschmidt")
    db.add(player)
    db.flush()
    _ratings(db, player, start=EVENT_DATE, end=EVENT_DATE)
    _ratings(
        db,
        player,
        start=EVENT_DATE,
        end=dt.date(2026, 9, 2),
    )

    assert _resolve(db, player) is None


def test_filtra_version_comparable(db):
    player = Player(mlb_id=814439, full_name="Ryan Waldschmidt")
    db.add(player)
    db.flush()
    _ratings(
        db,
        player,
        start=dt.date(2026, 8, 1),
        end=dt.date(2026, 8, 24),
        model="ratings-3.0",
    )

    assert _resolve(db, player) is None
