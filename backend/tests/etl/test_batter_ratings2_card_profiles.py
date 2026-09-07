"""Integración de rarity-2.0 en perfiles BATTER."""

import datetime as dt

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CardGenerationProfile, Player, PlayerRatings, PlayerSeason
from app.models import RatingDistribution
from app.models.card import CardRarity
from etl.services.ratings2_card_profiles import (
    generate_batter_card_profile_from_ratings2,
    generate_card_profile_from_ratings2,
    generate_pitcher_card_profile_from_ratings2,
)


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)
BATTER_HISTOGRAM = {
    "63": 1,
    "64": 4,
    "65": 1,
    "66": 3,
    "67": 17,
    "68": 17,
    "69": 33,
    "70": 50,
    "71": 42,
    "72": 23,
    "73": 17,
    "74": 9,
    "75": 5,
    "77": 1,
    "78": 2,
}


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


def _seed(db, *, add_distribution=True):
    player = Player(
        mlb_id=660271,
        full_name="Shohei Ohtani",
        primary_position="TWP",
    )
    db.add(player)
    db.flush()
    season = PlayerSeason(
        player_id=player.id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )
    db.add(season)
    db.flush()
    ratings = PlayerRatings(
        player_id=player.id,
        season=2026,
        role="BATTER",
        rating_model_version="ratings-2.0",
        distribution_version="dist-1.0",
        data_start_date=START,
        data_end_date=END,
        contact_rating=56,
        power_rating=68,
        vision_rating=66,
        clutch_rating=70,
        overall_rating=64,
        input_hash="o" * 64,
    )
    db.add(ratings)
    if add_distribution:
        db.add(RatingDistribution(
            season=2026,
            role="BATTER",
            rating_model_version="ratings-2.0",
            source_distribution_version="dist-1.0",
            rarity_model_version="rarity-2.0",
            metric="overall_rating",
            population_size=225,
            population_histogram=BATTER_HISTOGRAM,
            minimum=63,
            p05=67,
            p10=67,
            p25=69,
            p50=70,
            p75=72,
            p90=73,
            p95=74,
            maximum=78,
            population_mean=70,
            data_start_date=START,
            data_end_date=END,
        ))
    db.commit()
    return season, ratings


def test_ohtani_copia_batter_ratings_rarity_common_y_es_idempotente(db):
    season, ratings = _seed(db)
    first = generate_card_profile_from_ratings2(
        db,
        player_ratings_id=ratings.id,
        player_season_id=season.id,
    )
    assert first.status == "CREATED"
    profile = db.query(CardGenerationProfile).one()
    assert profile.player_ratings_id == ratings.id
    assert profile.role == "BATTER"
    assert (
        profile.contact_rating,
        profile.power_rating,
        profile.vision_rating,
        profile.clutch_rating,
        profile.overall_rating,
    ) == (56, 68, 66, 70, 64)
    assert (
        profile.velocity_rating,
        profile.control_rating,
        profile.movement_rating,
        profile.stuff_rating,
    ) == (None, None, None, None)
    assert profile.performance_tier == CardRarity.COMMON
    assert profile.calculated_rarity == CardRarity.COMMON
    assert profile.calculation_metadata["card_rarity_status"] == "PENDING_CARD_EDITION"
    assert profile.calculation_metadata["performance_percentile"] == pytest.approx(3 / 225)
    assert "rarity_percentile" not in profile.calculation_metadata
    assert profile.calculation_metadata["rating_distribution_histogram"] == BATTER_HISTOGRAM
    assert profile.calculation_metadata["traits_status"] == "PENDING_TRAITS_2.0"

    second = generate_card_profile_from_ratings2(
        db, player_ratings_id=ratings.id, player_season_id=season.id
    )
    assert second.status == "UNCHANGED"
    assert second.card_generation_profile_id == first.card_generation_profile_id


def test_cambio_de_distribucion_actualiza_fingerprint_y_performance_tier(db):
    _season, ratings = _seed(db)
    generate_batter_card_profile_from_ratings2(db, player_ratings_id=ratings.id)
    profile = db.query(CardGenerationProfile).one()
    original_hash = profile.input_hash
    distribution = db.query(RatingDistribution).one()
    distribution.population_histogram = {"63": 221, "64": 4}
    db.commit()

    result = generate_batter_card_profile_from_ratings2(
        db, player_ratings_id=ratings.id
    )
    db.refresh(profile)
    assert result.status == "UPDATED"
    assert profile.input_hash != original_hash
    assert profile.performance_tier == CardRarity.DIAMOND
    assert profile.calculated_rarity == CardRarity.COMMON
    assert profile.calculation_metadata["performance_percentile"] == pytest.approx(223 / 225)


def test_sin_distribucion_batter_exacta_no_genera_perfil(db):
    _season, ratings = _seed(db, add_distribution=False)
    # Una distribución de otro rol nunca debe utilizarse como fallback.
    db.add(RatingDistribution(
        season=2026,
        role="PITCHER",
        rating_model_version="ratings-2.0",
        source_distribution_version="dist-1.0",
        rarity_model_version="rarity-2.0",
        metric="overall_rating",
        population_size=1,
        population_histogram={"64": 1},
        minimum=64,
        p05=64,
        p10=64,
        p25=64,
        p50=64,
        p75=64,
        p90=64,
        p95=64,
        maximum=64,
        population_mean=64,
        data_start_date=START,
        data_end_date=END,
    ))
    db.commit()

    result = generate_batter_card_profile_from_ratings2(
        db, player_ratings_id=ratings.id
    )
    assert result.status == "SKIPPED_NO_RATING_DISTRIBUTION"
    assert result.card_generation_profile_id is None
    assert db.query(CardGenerationProfile).count() == 0


def test_adaptador_batter_rechaza_player_ratings_pitcher(db):
    _season, ratings = _seed(db)
    ratings.role = "PITCHER"
    ratings.contact_rating = None
    ratings.power_rating = None
    ratings.vision_rating = None
    ratings.clutch_rating = None
    ratings.velocity_rating = 64
    ratings.control_rating = 64
    ratings.movement_rating = 64
    ratings.stuff_rating = 64
    db.commit()

    with pytest.raises(ValueError, match="rol BATTER"):
        generate_batter_card_profile_from_ratings2(
            db, player_ratings_id=ratings.id
        )


def test_twp_conserva_perfiles_batter_y_pitcher_independientes(db):
    season, batter_ratings = _seed(db)
    player = batter_ratings.player
    pitcher_ratings = PlayerRatings(
        player_id=player.id,
        season=2026,
        role="PITCHER",
        rating_model_version="ratings-2.0",
        distribution_version="dist-1.0",
        data_start_date=START,
        data_end_date=END,
        velocity_rating=71,
        control_rating=71,
        movement_rating=77,
        stuff_rating=79,
        overall_rating=75,
        input_hash="p" * 64,
    )
    db.add(pitcher_ratings)
    db.add(RatingDistribution(
        season=2026,
        role="PITCHER",
        rating_model_version="ratings-2.0",
        source_distribution_version="dist-1.0",
        rarity_model_version="rarity-2.0",
        metric="overall_rating",
        population_size=1,
        population_histogram={"75": 1},
        minimum=75,
        p05=75,
        p10=75,
        p25=75,
        p50=75,
        p75=75,
        p90=75,
        p95=75,
        maximum=75,
        population_mean=75,
        data_start_date=START,
        data_end_date=END,
    ))
    db.commit()

    assert generate_batter_card_profile_from_ratings2(
        db, player_ratings_id=batter_ratings.id, player_season_id=season.id
    ).status == "CREATED"
    assert generate_pitcher_card_profile_from_ratings2(
        db, player_ratings_id=pitcher_ratings.id, player_season_id=season.id
    ).status == "CREATED"
    assert db.query(CardGenerationProfile).count() == 2
    assert {
        profile.role for profile in db.query(CardGenerationProfile).all()
    } == {"BATTER", "PITCHER"}
