"""Integridad del vínculo transicional CardGenerationProfile→PlayerRatings."""

import datetime as dt

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CardGenerationProfile, Player, PlayerRatings, PlayerSeason


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    player = Player(mlb_id=650911, full_name="Cristopher Sanchez", primary_position="SP")
    session.add(player)
    session.flush()
    season = PlayerSeason(
        player_id=player.id, season=2026, data_start_date=START, data_end_date=END
    )
    session.add(season)
    session.flush()
    yield session, player, season
    session.close()
    engine.dispose()


def _ratings(player):
    return PlayerRatings(
        player_id=player.id, season=2026, role="PITCHER",
        rating_model_version="ratings-2.0", distribution_version="dist-1.0",
        data_start_date=START, data_end_date=END,
        velocity_rating=71, control_rating=71, movement_rating=77, stuff_rating=79,
        overall_rating=75, input_hash="a" * 64,
    )


def _profile(season, **overrides):
    values = dict(
        player_season_id=season.id, rating_model_version="ratings-1.0",
        contact_rating=0, power_rating=0, vision_rating=0, clutch_rating=30,
        velocity_rating=71, control_rating=71, movement_rating=77,
        overall_rating=75, calculation_metadata={},
    )
    values.update(overrides)
    return CardGenerationProfile(**values)


def test_legacy_sin_player_ratings_sigue_valido(db):
    session, _player, season = db
    profile = _profile(season)
    session.add(profile)
    session.commit()
    assert profile.player_ratings_id is None
    assert profile.player_ratings is None
    assert profile.stuff_rating is None


def test_vinculo_valido_expone_relacion_orm(db):
    session, player, season = db
    ratings = _ratings(player)
    session.add(ratings)
    session.flush()
    profile = _profile(
        season, rating_model_version="ratings-2.0", player_ratings_id=ratings.id,
        stuff_rating=79,
    )
    session.add(profile)
    session.commit()
    assert profile.player_ratings is ratings
    assert ratings.card_generation_profiles == [profile]
    assert profile.stuff_rating == 79


@pytest.mark.parametrize("stuff_rating", [-1, 100])
def test_stuff_rating_fuera_de_rango_es_rechazado(db, stuff_rating):
    session, _player, season = db
    session.add(_profile(season, stuff_rating=stuff_rating))
    with pytest.raises(IntegrityError):
        session.flush()


def test_fk_rechaza_rating_model_version_inconsistente(db):
    session, player, season = db
    ratings = _ratings(player)
    session.add(ratings)
    session.flush()
    session.add(_profile(
        season, rating_model_version="ratings-1.0", player_ratings_id=ratings.id
    ))
    with pytest.raises(IntegrityError):
        session.flush()
