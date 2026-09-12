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
    RatingDistribution,
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
from etl.services.rarity_policies import RARITY_POLICY_VERSION


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


def _publication_context(db, *, rating_model_version="ratings-2.0", edition=None):
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
    if edition is not None:
        if edition.id is None:
            db.add(edition)
            db.flush()
    else:
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


def _generation_profile(
    db,
    player_season,
    ratings,
    *,
    calculated_rarity=CardRarity.COMMON,
    calculation_metadata=None,
):
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
        calculated_rarity=calculated_rarity,
        primary_batter_trait=None,
        primary_pitcher_trait=None,
        repertoire_payload=None,
        calculation_metadata=calculation_metadata or {"adapter_version": "fixture"},
    )
    db.add(profile)
    db.flush()
    return profile


def _rating_distribution(db, *, histogram=None, role="BATTER"):
    histogram = {
        int(key): int(value) for key, value in (histogram or {"64": 5, "80": 5}).items()
    }
    population_size = sum(histogram.values())
    lo, hi = min(histogram), max(histogram)
    dist = RatingDistribution(
        season=2026,
        role=role,
        rating_model_version="ratings-2.0",
        source_distribution_version="dist-1.0",
        rarity_model_version="rarity-2.0",
        metric="overall_rating",
        population_size=population_size,
        population_histogram={str(k): v for k, v in histogram.items()},
        minimum=lo,
        p05=lo,
        p10=lo,
        p25=lo,
        p50=lo + (hi - lo) // 2,
        p75=hi,
        p90=hi,
        p95=hi,
        maximum=hi,
        population_mean=(lo + hi) / 2,
        data_start_date=START,
        data_end_date=END,
    )
    db.add(dist)
    db.flush()
    return dist


def _rarity_policy_edition(db, code="2026_BASE_RARITY"):
    edition = CardEdition(
        code=code,
        name="Base Rarity",
        edition_type=CardEditionType.BASE,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.SYSTEM,
        rating_policy_version="base-card-ratings-1.0",
        rarity_policy_version=RARITY_POLICY_VERSION,
        metadata_payload={},
    )
    db.add(edition)
    db.flush()
    return edition


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


def test_resuelve_politica_declarada_sin_ambiguedad(db):
    team, player, player_season, edition = _publication_context(db)
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    declared = generate_card_rating_profile(
        db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
    )
    # Perfil especulativo de una política futura (base-card-ratings-1.1):
    # coexiste bajo la misma identidad salvo rating_policy_version, y NO debe
    # enmascarar a la política que la edición declara.
    db.add(
        CardRatingProfile(
            player_id=player.id,
            card_edition_id=edition.id,
            role="BATTER",
            rating_policy_version="base-card-ratings-1.1",
            contact_rating=56,
            power_rating=88,
            vision_rating=66,
            clutch_rating=70,
            overall_rating=70,
            source_player_ratings_id=ratings.id,
            input_hash="d" * 64,
            metadata_payload={"fixture": "futura-politica"},
        )
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
    assert card.card_rating_profile_id == declared.card_rating_profile_id
    assert (card.overall, card.power) == (64, 68)


def test_edicion_sin_politica_declarada_fallbacks_a_generation_profile(db):
    team, player, player_season, edition = _publication_context(
        db,
        edition=CardEdition(
            code="2026_BASE_LEGACY",
            name="Base Legacy",
            edition_type=CardEditionType.BASE,
            season=2026,
            version="edition-1.0",
            source_type=CardEditionSourceType.SYSTEM,
            metadata_payload={},
        ),
    )
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
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
    assert card.generation_profile_id is not None
    assert (card.overall, card.power) == (64, 68)


def test_edicion_sin_rarity_policy_conserva_calculated_rarity(db):
    team, player, player_season, edition = _publication_context(db)
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings, calculated_rarity=CardRarity.GOLD)
    generate_card_rating_profile(
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
    assert card.card_rating_profile_id is not None
    assert card.rarity == CardRarity.GOLD


def test_edicion_con_rarity_policy_resuelve_sobre_ovr_final(db):
    team, player, player_season, edition = _publication_context(
        db, edition=_rarity_policy_edition(db)
    )
    ratings = _batter_ratings(db, player)
    distribution = _rating_distribution(db)
    _generation_profile(
        db,
        player_season,
        ratings,
        calculated_rarity=CardRarity.GOLD,
        calculation_metadata={
            "adapter_version": "fixture",
            "rating_distribution_id": distribution.id,
            "performance_tier_model_version": "rarity-2.0",
        },
    )
    generate_card_rating_profile(
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

    # OVR 64 en histograma {"64": 5, "80": 5} -> percentil 0.25 -> COMMON.
    # NO hereda el calculated_rarity legacy (GOLD).
    assert result.status == "ACTIVE"
    assert card.rarity == CardRarity.COMMON


def test_edicion_con_rarity_policy_sin_distribucion_falla_publicacion(db):
    team, player, player_season, edition = _publication_context(
        db,
        edition=_rarity_policy_edition(db, code="2026_BASE_RARITY_FAIL"),
    )
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    db.commit()

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )

    assert result.status == "FAILED"
    assert db.query(PlayerCardModel).count() == 0
    assert any("rating_distribution_id" in issue for issue in result.issues)