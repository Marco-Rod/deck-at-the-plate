"""Publicación consumes CardRatingProfile como fuente autoritativa de atributos."""

import datetime as dt

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    CardGenerationProfile,
    CardRatingProfile,
    GamePlayerIdentity,
    Player,
    PlayerCardModel,
    PlayerRatings,
    PlayerSeason,
    SourceTeam,
    SourceTeamGameTeamMapping,
    SourceTeamRosterMember,
    SourceTeamRosterSnapshot,
    Team,
)
from app.models.card import CardRarity
from app.services.card_editions import ensure_system_base_edition
from etl.services.card_catalog import publish_card_catalog
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


def _publication_context(db, *, rating_model_version="ratings-2.0"):
    team = Team(id="team-1", abbreviation="TST", name="Test Team", city="Test City")
    source_team = SourceTeam(
        source="MLB",
        external_id=1,
        source_name="Source Team",
        source_abbreviation="SRC",
    )
    player = Player(mlb_id=660271, full_name="Sample Slugger", primary_position="DH")
    db.add_all([team, source_team, player])
    db.flush()
    db.add(SourceTeamGameTeamMapping(
        source_team_id=source_team.id,
        team_id=team.id,
        valid_from=START,
    ))
    snapshot = SourceTeamRosterSnapshot(
        source_team_id=source_team.id,
        season=2026,
        as_of_date=END,
    )
    db.add(snapshot)
    db.flush()
    db.add(SourceTeamRosterMember(
        roster_snapshot_id=snapshot.id,
        player_id=player.id,
        status="ACTIVE",
        position="DH",
    ))
    db.add(GamePlayerIdentity(
        player_id=player.id,
        display_first_name="Sample",
        display_last_name="Slugger",
        display_name="Sample Slugger",
    ))
    player_season = PlayerSeason(
        player_id=player.id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )
    db.add(player_season)
    db.flush()
    edition = ensure_system_base_edition(db, season=2026)
    return team, player, player_season, edition


def _batter_ratings(db, player):
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
        input_hash="a" * 64,
    )
    db.add(ratings)
    db.flush()
    return ratings


def _generation_profile(db, player_season, ratings):
    profile = CardGenerationProfile(
        player_season_id=player_season.id,
        rating_model_version="ratings-2.0",
        role="BATTER",
        player_ratings_id=ratings.id,
        input_hash="b" * 64,
        contact_rating=56,
        power_rating=68,
        vision_rating=66,
        clutch_rating=70,
        velocity_rating=None,
        control_rating=None,
        movement_rating=None,
        stuff_rating=None,
        overall_rating=64,
        calculated_rarity=CardRarity.COMMON,
        primary_batter_trait=None,
        primary_pitcher_trait=None,
        repertoire_payload=None,
        calculation_metadata={"adapter_version": "fixture"},
    )
    db.add(profile)
    db.flush()
    return profile


def test_publica_atributos_desde_card_rating_profile(db):
    team, player, player_season, edition = _publication_context(db)
    ratings = _batter_ratings(db, player)
    profile = _generation_profile(db, player_season, ratings)
    rating = generate_card_rating_profile(
        db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
    )
    db.commit()

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    card = db.query(PlayerCardModel).one()

    assert result.status == "ACTIVE"
    assert card.card_rating_profile_id == rating.card_rating_profile_id
    assert card.generation_profile_id == profile.id
    assert (card.overall, card.contact, card.power) == (64, 56, 68)
    assert (card.vision, card.clutch, card.velocity) == (66, 70, 0)
    assert card.rarity == CardRarity.COMMON


def test_publicacion_es_idempotente_con_rating_profile(db):
    _team, player, player_season, edition = _publication_context(db)
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    generate_card_rating_profile(
        db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
    )
    db.commit()

    first = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    card_id = db.query(PlayerCardModel).one().id
    second = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )

    assert first.status == second.status == "ACTIVE"
    assert db.query(PlayerCardModel).count() == 1
    assert db.query(PlayerCardModel).one().id == card_id


def test_fallback_generation_profile_sin_rating_profile(db):
    team, player, player_season, edition = _publication_context(db)
    ratings = _batter_ratings(db, player)
    profile = _generation_profile(db, player_season, ratings)
    db.commit()

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    card = db.query(PlayerCardModel).one()

    assert result.status == "ACTIVE"
    assert card.card_rating_profile_id is None
    assert card.generation_profile_id == profile.id
    assert (card.overall, card.contact, card.power, card.clutch) == (64, 56, 68, 70)


def test_fallback_sin_anclaje_a_player_ratings(db):
    team, player, player_season, edition = _publication_context(db)
    profile = CardGenerationProfile(
        player_season_id=player_season.id,
        rating_model_version="ratings-1.0",
        role=None,
        player_ratings_id=None,
        input_hash="c" * 64,
        contact_rating=70,
        power_rating=70,
        vision_rating=70,
        clutch_rating=70,
        velocity_rating=0,
        control_rating=0,
        movement_rating=0,
        overall_rating=70,
        calculated_rarity=CardRarity.BRONZE,
        calculation_metadata={},
    )
    db.add(profile)
    db.commit()

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-1.0",
        data_end_date=END,
    )
    card = db.query(PlayerCardModel).one()

    assert result.status == "ACTIVE"
    assert card.card_rating_profile_id is None
    assert card.rarity == CardRarity.BRONZE
    assert db.query(CardRatingProfile).count() == 0