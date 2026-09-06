"""Pruebas del adaptador PlayerRatings→CardGenerationProfile ratings-2.0."""

import datetime as dt

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CardGenerationProfile, Player, PlayerRatings, PlayerSeason, RatingDistribution
from app.models.card import CardRarity
from etl.services.ratings2_card_profiles import generate_pitcher_card_profile_from_ratings2


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    @event.listens_for(engine, "connect")
    def _foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _seed(db, *, mlb_id=650911, version="ratings-2.0", start=START, end=END):
    player = Player(mlb_id=mlb_id, full_name=f"Player {mlb_id}", primary_position="SP")
    db.add(player)
    db.flush()
    season = PlayerSeason(
        player_id=player.id, season=2026, data_start_date=start, data_end_date=end
    )
    db.add(season)
    db.flush()
    ratings = PlayerRatings(
        player_id=player.id, season=2026, role="PITCHER",
        rating_model_version=version, distribution_version="dist-1.0",
        data_start_date=start, data_end_date=end,
        velocity_rating=71, control_rating=71, movement_rating=77, stuff_rating=79,
        overall_rating=75, input_hash="a" * 64,
    )
    db.add(ratings)
    if version == "ratings-2.0" and db.query(RatingDistribution).filter_by(
        season=2026,
        role="PITCHER",
        rating_model_version=version,
        source_distribution_version="dist-1.0",
        rarity_model_version="rarity-2.0",
        metric="overall_rating",
        data_start_date=start,
        data_end_date=end,
    ).one_or_none() is None:
        db.add(RatingDistribution(
            season=2026,
            role="PITCHER",
            rating_model_version=version,
            source_distribution_version="dist-1.0",
            rarity_model_version="rarity-2.0",
            metric="overall_rating",
            population_size=39,
            population_histogram={
                "63": 1, "64": 2, "66": 3, "67": 5, "68": 3, "69": 8,
                "70": 6, "71": 4, "72": 1, "73": 1, "74": 1, "75": 4,
            },
            minimum=63,
            p05=64,
            p10=66,
            p25=67,
            p50=69,
            p75=71,
            p90=74.2,
            p95=75,
            maximum=75,
            population_mean=69.31,
            data_start_date=start,
            data_end_date=end,
        ))
    db.commit()
    return player, season, ratings


def test_copia_ratings_sin_recalcular_y_es_idempotente(db):
    _player, season, ratings = _seed(db)
    first = generate_pitcher_card_profile_from_ratings2(
        db, player_ratings_id=ratings.id, player_season_id=season.id
    )
    assert first.status == "CREATED"
    profile = db.query(CardGenerationProfile).one()
    assert profile.player_ratings_id == ratings.id
    assert profile.rating_model_version == "ratings-2.0"
    assert (
        profile.velocity_rating, profile.control_rating, profile.movement_rating,
        profile.stuff_rating, profile.overall_rating,
    ) == (71, 71, 77, 79, 75)
    assert profile.calculated_rarity == CardRarity.GOLD
    assert profile.calculation_metadata["rarity_model_version"] == "rarity-2.0"
    assert profile.calculation_metadata["rarity_percentile"] == pytest.approx(37 / 39)
    assert profile.primary_pitcher_trait is None
    assert profile.calculation_metadata["traits_status"] == "NO_TRAIT"

    second = generate_pitcher_card_profile_from_ratings2(
        db, player_ratings_id=ratings.id, player_season_id=season.id
    )
    assert second.status == "UNCHANGED"
    assert db.query(CardGenerationProfile).count() == 1


def test_actualiza_si_cambia_snapshot_oficial_de_ratings(db):
    _player, season, ratings = _seed(db)
    generate_pitcher_card_profile_from_ratings2(db, player_ratings_id=ratings.id)
    ratings.stuff_rating = 80
    ratings.input_hash = "b" * 64
    db.commit()
    result = generate_pitcher_card_profile_from_ratings2(db, player_ratings_id=ratings.id)
    assert result.status == "UPDATED"
    assert db.query(CardGenerationProfile).one().stuff_rating == 80
    assert db.query(CardGenerationProfile).one().primary_pitcher_trait is None


def test_asigna_trait_calculado_sin_recalcular_ratings(db):
    _player, _season, ratings = _seed(db)
    ratings.velocity_rating = 95
    ratings.control_rating = 70
    ratings.movement_rating = 70
    ratings.stuff_rating = 70
    ratings.overall_rating = 75
    ratings.input_hash = "c" * 64
    db.commit()

    generate_pitcher_card_profile_from_ratings2(db, player_ratings_id=ratings.id)

    profile = db.query(CardGenerationProfile).one()
    assert profile.primary_pitcher_trait == "HIGH_HEAT"
    assert profile.calculation_metadata["traits_status"] == "ASSIGNED"
    assert profile.velocity_rating == ratings.velocity_rating


def test_cambio_de_distribucion_actualiza_rarity_y_perfil(db):
    _player, _season, ratings = _seed(db)
    first = generate_pitcher_card_profile_from_ratings2(
        db, player_ratings_id=ratings.id
    )
    profile = db.query(CardGenerationProfile).one()
    first_hash = profile.input_hash
    distribution = db.query(RatingDistribution).one()
    distribution.population_size = 20
    distribution.population_histogram = {"60": 19, "75": 1}
    db.commit()

    changed = generate_pitcher_card_profile_from_ratings2(
        db, player_ratings_id=ratings.id
    )

    db.refresh(profile)
    assert first.status == "CREATED"
    assert changed.status == "UPDATED"
    assert profile.calculated_rarity == CardRarity.DIAMOND
    assert profile.input_hash != first_hash


def test_distribucion_inexistente_no_genera_perfil_ni_fallback(db):
    _player, _season, ratings = _seed(db)
    db.delete(db.query(RatingDistribution).one())
    db.commit()

    result = generate_pitcher_card_profile_from_ratings2(
        db, player_ratings_id=ratings.id
    )

    assert result.status == "SKIPPED_NO_RATING_DISTRIBUTION"
    assert result.card_generation_profile_id is None
    assert db.query(CardGenerationProfile).count() == 0


def test_rechaza_otro_jugador_snapshot_o_version(db):
    _player, season, ratings = _seed(db)
    _other, other_season, _other_ratings = _seed(
        db, mlb_id=660271, start=dt.date(2026, 8, 1), end=END
    )
    with pytest.raises(ValueError, match="jugador/snapshot"):
        generate_pitcher_card_profile_from_ratings2(
            db, player_ratings_id=ratings.id, player_season_id=other_season.id
        )

    _legacy_player, _legacy_season, legacy_ratings = _seed(db, mlb_id=123, version="ratings-1.0")
    with pytest.raises(ValueError, match="modelo inesperado"):
        generate_pitcher_card_profile_from_ratings2(db, player_ratings_id=legacy_ratings.id)
