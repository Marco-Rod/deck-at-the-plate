"""CardRatingProfile conserva identidad, roles y provenance por edición."""

import datetime as dt

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    CardRatingProfile,
    Player,
    PlayerRatings,
)
from etl.services.card_rating_profiles import generate_card_rating_profile


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
    yield session
    session.close()
    engine.dispose()


def _player(db, mlb_id=660271):
    player = Player(
        mlb_id=mlb_id, full_name=f"Player {mlb_id}", primary_position="TWP"
    )
    db.add(player)
    db.flush()
    return player


def _edition(db, *, code="2026_BASE", edition_type=CardEditionType.BASE, season=2026):
    edition = CardEdition(
        code=code,
        name=code.replace("_", " ").title(),
        edition_type=edition_type,
        season=season,
        version="edition-1.0",
        source_type=CardEditionSourceType.SYSTEM,
        metadata_payload={"fixture": code},
    )
    db.add(edition)
    db.flush()
    return edition


def _batter_ratings(db, player, **overrides):
    values = {
        "player_id": player.id,
        "season": 2026,
        "role": "BATTER",
        "rating_model_version": "ratings-2.0",
        "distribution_version": "dist-1.0",
        "data_start_date": START,
        "data_end_date": END,
        "contact_rating": 56,
        "power_rating": 68,
        "vision_rating": 66,
        "clutch_rating": 70,
        "overall_rating": 64,
        "input_hash": "a" * 64,
    }
    values.update(overrides)
    ratings = PlayerRatings(**values)
    db.add(ratings)
    db.flush()
    return ratings


def _pitcher_ratings(db, player):
    ratings = PlayerRatings(
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
    db.add(ratings)
    db.flush()
    return ratings


def test_copia_ratings_sin_boost_y_es_idempotente(db):
    player = _player(db)
    ratings = _batter_ratings(db, player)
    edition = _edition(db)
    db.commit()

    created = generate_card_rating_profile(
        db,
        source_player_ratings_id=ratings.id,
        card_edition_id=edition.id,
    )
    unchanged = generate_card_rating_profile(
        db,
        source_player_ratings_id=ratings.id,
        card_edition_id=edition.id,
    )
    profile = db.get(CardRatingProfile, created.card_rating_profile_id)

    assert created.status == "CREATED"
    assert unchanged.status == "UNCHANGED"
    assert unchanged.card_rating_profile_id == created.card_rating_profile_id
    assert db.query(CardRatingProfile).count() == 1
    assert (profile.contact_rating, profile.power_rating) == (56, 68)
    assert (profile.vision_rating, profile.clutch_rating, profile.overall_rating) == (
        66,
        70,
        64,
    )
    assert profile.velocity_rating is None
    assert profile.metadata_payload["transformation"] == "IDENTITY_COPY"


def test_mismo_jugador_puede_tener_base_y_moment_con_los_mismos_ratings(db):
    player = _player(db)
    ratings = _batter_ratings(db, player)
    base = _edition(db)
    moment = _edition(
        db, code="2026_MOMENT_001", edition_type=CardEditionType.MOMENT
    )
    db.commit()

    first = generate_card_rating_profile(
        db, source_player_ratings_id=ratings.id, card_edition_id=base.id
    )
    second = generate_card_rating_profile(
        db,
        source_player_ratings_id=ratings.id,
        card_edition_id=moment.id,
        policy_reason="Contrato MOMENT sin boosts automáticos",
    )

    assert first.card_rating_profile_id != second.card_rating_profile_id
    assert db.query(CardRatingProfile).count() == 2
    assert {row.overall_rating for row in db.query(CardRatingProfile)} == {64}


def test_moment_persiste_transformacion_y_actualiza_si_cambian_ajustes(db):
    player = _player(db)
    ratings = _batter_ratings(db, player)
    moment = _edition(
        db, code="2026_WALK_OFF", edition_type=CardEditionType.MOMENT
    )
    db.commit()

    created = generate_card_rating_profile(
        db,
        source_player_ratings_id=ratings.id,
        card_edition_id=moment.id,
        policy_adjustments={
            "power_rating": 12,
            "clutch_rating": 18,
        },
        policy_reason="Walk-off con dos home runs",
    )
    profile = db.get(CardRatingProfile, created.card_rating_profile_id)
    assert created.status == "CREATED"
    assert (profile.power_rating, profile.clutch_rating, profile.overall_rating) == (
        80,
        88,
        71,
    )
    assert profile.metadata_payload["base_ratings"]["power_rating"] == 68
    assert profile.metadata_payload["adjustments"]["power_rating"] == 12
    assert profile.metadata_payload["reason"] == "Walk-off con dos home runs"

    updated = generate_card_rating_profile(
        db,
        source_player_ratings_id=ratings.id,
        card_edition_id=moment.id,
        policy_adjustments={
            "power_rating": 15,
            "clutch_rating": 18,
        },
        policy_reason="Walk-off con dos home runs",
    )
    db.refresh(profile)
    assert updated.status == "UPDATED"
    assert updated.card_rating_profile_id == created.card_rating_profile_id
    assert (profile.power_rating, profile.overall_rating) == (83, 71)


def test_actualiza_si_cambia_el_snapshot_fuente(db):
    player = _player(db)
    ratings = _batter_ratings(db, player)
    edition = _edition(db)
    db.commit()
    created = generate_card_rating_profile(
        db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
    )

    ratings.power_rating = 70
    ratings.overall_rating = 65
    ratings.input_hash = "b" * 64
    db.commit()
    updated = generate_card_rating_profile(
        db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
    )
    profile = db.get(CardRatingProfile, created.card_rating_profile_id)

    assert updated.status == "UPDATED"
    assert updated.card_rating_profile_id == created.card_rating_profile_id
    assert updated.input_hash != created.input_hash
    assert (profile.power_rating, profile.overall_rating) == (70, 65)


def test_pitcher_conserva_solo_sus_atributos(db):
    player = _player(db, mlb_id=650911)
    ratings = _pitcher_ratings(db, player)
    edition = _edition(db)
    db.commit()

    result = generate_card_rating_profile(
        db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
    )
    profile = db.get(CardRatingProfile, result.card_rating_profile_id)

    assert (profile.velocity_rating, profile.control_rating) == (71, 71)
    assert (profile.movement_rating, profile.stuff_rating, profile.overall_rating) == (
        77,
        79,
        75,
    )
    assert profile.contact_rating is None


def test_fk_compuesta_rechaza_fuente_de_otro_jugador(db):
    source_player = _player(db)
    other_player = _player(db, mlb_id=650911)
    ratings = _batter_ratings(db, source_player)
    edition = _edition(db)
    db.commit()

    db.add(
        CardRatingProfile(
            player_id=other_player.id,
            card_edition_id=edition.id,
            role="BATTER",
            contact_rating=56,
            power_rating=68,
            vision_rating=66,
            clutch_rating=70,
            overall_rating=64,
            source_player_ratings_id=ratings.id,
            rating_policy_version="card-ratings-1.0",
            input_hash="x" * 64,
            metadata_payload={},
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_rechaza_edicion_de_otra_temporada(db):
    player = _player(db)
    ratings = _batter_ratings(db, player)
    edition = _edition(db, code="2027_BASE", season=2027)
    db.commit()

    with pytest.raises(ValueError, match="temporadas distintas"):
        generate_card_rating_profile(
            db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
        )


def test_modelo_no_define_rarity_ni_boosts():
    columns = set(CardRatingProfile.__table__.columns.keys())
    assert "rarity" not in columns
    assert "boosts" not in columns
    assert "rating_boost" not in columns
