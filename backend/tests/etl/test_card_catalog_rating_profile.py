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
from etl.services.card_catalog import publish_card_catalog
from etl.services.base_eligibility_policy import (
    BASE_ELIGIBILITY_POLICY_VERSION,
    ELIGIBLE,
    INELIGIBLE,
    PROVISIONAL,
)
from etl.services.card_rating_policies import BASE_RATING_POLICY_VERSION
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


def _publication_context(
    db,
    *,
    rating_model_version="ratings-2.0",
    edition=None,
    primary_position="DH",
    mlb_id=660271,
    name="Sample Slugger",
    team_key="team-1",
    source_external_id=1,
):
    team = Team(
        id=team_key,
        abbreviation=f"T{source_external_id}",
        name=f"Test Team {source_external_id}",
        city="Test City",
    )
    source_team = SourceTeam(
        source="MLB",
        external_id=source_external_id,
        source_name=f"Source Team {source_external_id}",
        source_abbreviation="SRC",
    )
    player = Player(mlb_id=mlb_id, full_name=name, primary_position=primary_position)
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
        display_first_name="First",
        display_last_name=name,
        display_name=name,
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
        # Este fixture cubre la transición de ratings. No declara eligibility:
        # conserva explícitamente el comportamiento legacy de publicación.
        edition = db.query(CardEdition).filter_by(
            code="2026_BASE_RATING_LEGACY", season=2026, version="edition-1.0"
        ).one_or_none()
        if edition is None:
            edition = CardEdition(
                code="2026_BASE_RATING_LEGACY",
                name="Base Rating Legacy",
                edition_type=CardEditionType.BASE,
                season=2026,
                version="edition-1.0",
                source_type=CardEditionSourceType.SYSTEM,
                rating_policy_version=BASE_RATING_POLICY_VERSION,
                metadata_payload={},
            )
            db.add(edition)
            db.flush()
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


def _pitcher_ratings(db, player):
    ratings = PlayerRatings(
        player_id=player.id,
        season=2026,
        role="PITCHER",
        rating_model_version="ratings-2.0",
        distribution_version="dist-1.0",
        data_start_date=START,
        data_end_date=END,
        velocity_rating=78,
        control_rating=72,
        movement_rating=70,
        stuff_rating=74,
        overall_rating=75,
        input_hash="e" * 64,
    )
    db.add(ratings)
    db.flush()
    return ratings


def _pitcher_profile(db, player_season, ratings):
    profile = CardGenerationProfile(
        player_season_id=player_season.id,
        rating_model_version="ratings-2.0",
        role="PITCHER",
        player_ratings_id=ratings.id,
        input_hash="f" * 64,
        contact_rating=None,
        power_rating=None,
        vision_rating=None,
        clutch_rating=None,
        velocity_rating=78,
        control_rating=72,
        movement_rating=70,
        stuff_rating=74,
        overall_rating=75,
        calculated_rarity=CardRarity.COMMON,
        primary_batter_trait=None,
        primary_pitcher_trait=None,
        repertoire_payload=None,
        calculation_metadata={"adapter_version": "fixture"},
    )
    db.add(profile)
    db.flush()
    return profile


def test_two_way_gana_perfil_del_rol_primario_lanzador(db):
    # Bateador SP: DOS perfiles (BATTER insertado PRIMERO, orden adversarial).
    # La regla determinista debería ganar con el perfil PITCHER.
    team, player, player_season, edition = _publication_context(
        db, primary_position="SP"
    )
    batter_ratings = _batter_ratings(db, player)
    batter_profile = _generation_profile(db, player_season, batter_ratings)
    pitcher_ratings = _pitcher_ratings(db, player)
    pitcher_profile = _pitcher_profile(db, player_season, pitcher_ratings)
    db.commit()

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    cards = db.query(PlayerCardModel).all()

    assert result.status == "ACTIVE"
    assert len(cards) == 1
    assert cards[0].generation_profile_id == pitcher_profile.id
    assert cards[0].position == "SP"
    assert cards[0].velocity == 78
    assert cards[0].power == 0
    assert cards[0].generation_profile_id != batter_profile.id


def test_two_way_gana_perfil_del_rol_primario_bateador(db):
    # DH: PITCHER insertado PRIMERO (orden adversarial); debe ganar el BATTER.
    team, player, player_season, edition = _publication_context(
        db, primary_position="DH"
    )
    pitcher_ratings = _pitcher_ratings(db, player)
    pitcher_profile = _pitcher_profile(db, player_season, pitcher_ratings)
    batter_ratings = _batter_ratings(db, player)
    batter_profile = _generation_profile(db, player_season, batter_ratings)
    db.commit()

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    cards = db.query(PlayerCardModel).all()

    assert result.status == "ACTIVE"
    assert len(cards) == 1
    assert cards[0].generation_profile_id == batter_profile.id
    assert cards[0].position == "DH"
    assert cards[0].power == 68
    assert cards[0].velocity == 0
    assert cards[0].generation_profile_id != pitcher_profile.id


def test_normales_no_afectados_por_dedupe_two_way(db):
    # Dos jugadores distintos (un DH y un SP) publican DOS cartas, cada una
    # con su perfil de rol primario; el orden del catálogo es estable.
    team, player, player_season, edition = _publication_context(
        db, primary_position="DH", mlb_id=660271, name="A"
    )
    batter_ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, batter_ratings)

    team2, player2, player_season2, _ed2 = _publication_context(
        db,
        primary_position="SP",
        mlb_id=660272,
        name="B",
        team_key="team-2",
        source_external_id=2,
    )
    pitcher_ratings = _pitcher_ratings(db, player2)
    _pitcher_profile(db, player_season2, pitcher_ratings)
    db.commit()

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    cards = db.query(PlayerCardModel).order_by(PlayerCardModel.player_id).all()

    assert result.status == "ACTIVE"
    assert result.created == 2
    assert len(cards) == 2
    by_player = {c.player_id: c for c in cards}
    assert by_player[player.id].position == "DH"
    assert by_player[player2.id].position == "SP"
    assert by_player[player.id].velocity == 0
    assert by_player[player2.id].velocity == 78


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


def _eligibility_policy_edition(db, code="2026_BASE_ELIGIBILITY"):
    edition = CardEdition(
        code=code,
        name="Base Eligibility",
        edition_type=CardEditionType.BASE,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.SYSTEM,
        rating_policy_version=BASE_RATING_POLICY_VERSION,
        eligibility_policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
        metadata_payload={},
    )
    db.add(edition)
    db.flush()
    return edition


def _rating_with_eligibility(
    db,
    ratings,
    edition,
    *,
    status=PROVISIONAL,
    policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
):
    result = generate_card_rating_profile(
        db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
    )
    rating = db.get(CardRatingProfile, result.card_rating_profile_id)
    metadata = dict(rating.metadata_payload or {})
    metadata["eligibility"] = {
        "policy_version": policy_version,
        "status": status,
        "reasons": [],
    }
    rating.metadata_payload = metadata
    db.flush()
    return rating


@pytest.mark.parametrize("status", [PROVISIONAL, ELIGIBLE])
def test_eligibility_materializada_publica_y_habilita_pack(db, status):
    edition = _eligibility_policy_edition(db, code=f"2026_BASE_{status}")
    _team, player, player_season, _edition = _publication_context(
        db, edition=edition
    )
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    _rating_with_eligibility(db, ratings, edition, status=status)
    db.commit()

    result = publish_card_catalog(
        db, season=2026, card_edition_id=edition.id,
        rating_model_version="ratings-2.0", data_end_date=END,
    )

    card = db.query(PlayerCardModel).one()
    assert result.status == "ACTIVE"
    assert result.created == 1
    assert result.skipped_ineligible == 0
    assert card.is_active is True
    assert card.is_pack_eligible is True


def test_eligibility_ineligible_no_crea_carta_y_cuenta_skip(db):
    edition = _eligibility_policy_edition(db, code="2026_BASE_INELIGIBLE")
    _team, player, player_season, _edition = _publication_context(
        db, edition=edition
    )
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    _rating_with_eligibility(db, ratings, edition, status=INELIGIBLE)
    db.commit()

    result = publish_card_catalog(
        db, season=2026, card_edition_id=edition.id,
        rating_model_version="ratings-2.0", data_end_date=END,
    )

    assert result.status == "FAILED"  # no hay candidatos publicables es un gate válido
    assert result.skipped_ineligible == 1
    assert db.query(PlayerCardModel).count() == 0


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({}, "sin eligibility materializada"),
        (
            {
                "eligibility": {
                    "policy_version": "base-eligibility-1.0",
                    "status": PROVISIONAL,
                }
            },
            "no coincide",
        ),
        (
            {
                "eligibility": {
                    "policy_version": BASE_ELIGIBILITY_POLICY_VERSION,
                    "status": "UNKNOWN",
                }
            },
            "estado de eligibility inválido",
        ),
    ],
)
def test_eligibility_materializada_incompatible_falla_catalogo(db, metadata, message):
    edition = _eligibility_policy_edition(
        db, code=f"2026_BASE_FAIL_{message[:4]}"
    )
    _team, player, player_season, _edition = _publication_context(
        db, edition=edition
    )
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    rating = _rating_with_eligibility(db, ratings, edition)
    current = dict(rating.metadata_payload or {})
    current.pop("eligibility", None)
    current.update(metadata)
    rating.metadata_payload = current
    db.commit()

    result = publish_card_catalog(
        db, season=2026, card_edition_id=edition.id,
        rating_model_version="ratings-2.0", data_end_date=END,
    )

    assert result.status == "FAILED"
    assert db.query(PlayerCardModel).count() == 0
    assert any(message in issue for issue in result.issues)


def test_eligibility_declarada_exige_card_rating_profile(db):
    edition = _eligibility_policy_edition(db, code="2026_BASE_PROFILE_REQUIRED")
    _team, player, player_season, _edition = _publication_context(
        db, edition=edition
    )
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    db.commit()

    result = publish_card_catalog(
        db, season=2026, card_edition_id=edition.id,
        rating_model_version="ratings-2.0", data_end_date=END,
    )

    assert result.status == "FAILED"
    assert db.query(PlayerCardModel).count() == 0
    assert any("no existe CardRatingProfile" in issue for issue in result.issues)


def test_eligibility_mezcla_publica_solo_los_tres_validos_e_idempotente(db):
    edition = _eligibility_policy_edition(db, code="2026_BASE_ELIGIBILITY_MIX")
    statuses = (PROVISIONAL, PROVISIONAL, PROVISIONAL, INELIGIBLE)
    for index, status in enumerate(statuses, start=1):
        _team, player, player_season, _edition = _publication_context(
            db,
            edition=edition,
            mlb_id=660300 + index,
            name=f"Player {index}",
            team_key=f"eligibility-team-{index}",
            source_external_id=100 + index,
        )
        ratings = _batter_ratings(db, player)
        _generation_profile(db, player_season, ratings)
        _rating_with_eligibility(db, ratings, edition, status=status)
    db.commit()

    first = publish_card_catalog(
        db, season=2026, card_edition_id=edition.id,
        rating_model_version="ratings-2.0", data_end_date=END,
    )
    second = publish_card_catalog(
        db, season=2026, card_edition_id=edition.id,
        rating_model_version="ratings-2.0", data_end_date=END,
    )

    assert first.status == second.status == "ACTIVE"
    assert first.created == 3
    assert first.skipped_ineligible == 1
    assert second.created == 3
    assert db.query(PlayerCardModel).count() == 3
    assert db.query(PlayerCardModel).filter_by(is_pack_eligible=True).count() == 3


def test_eligibility_policy_desconocida_falla_aun_con_metadata_coincidente(db):
    """Versión no registrada en ELIGIBILITY_POLICIES es fail-closed en publicación.

    La generación ya la rechaza, pero publication no debe fiarse de que la
    metadata y la edición coincidan literalmente: expira un valor que la
    registry no reconoce y el catálogo debe invalidarse.
    """
    edition = _eligibility_policy_edition(db, code="2026_BASE_BANANA")
    _team, player, player_season, _edition = _publication_context(
        db, edition=edition
    )
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    _rating_with_eligibility(db, ratings, edition, status=PROVISIONAL)
    edition.eligibility_policy_version = "banana-9.0"
    rating = db.query(CardRatingProfile).one()
    current = dict(rating.metadata_payload or {})
    current["eligibility"] = {
        "policy_version": "banana-9.0",
        "status": PROVISIONAL,
        "reasons": [],
    }
    rating.metadata_payload = current
    db.commit()

    result = publish_card_catalog(
        db, season=2026, card_edition_id=edition.id,
        rating_model_version="ratings-2.0", data_end_date=END,
    )

    assert result.status == "FAILED"
    assert db.query(PlayerCardModel).count() == 0
    assert any("sin política de elegibilidad" in issue for issue in result.issues)


def test_eligibility_policy_incompatible_con_edicion_no_base_falla(db):
    edition = _eligibility_policy_edition(db, code="2026_MOMENT_ELIGIBILITY")
    _team, player, player_season, _edition = _publication_context(
        db, edition=edition
    )
    ratings = _batter_ratings(db, player)
    _generation_profile(db, player_season, ratings)
    _rating_with_eligibility(db, ratings, edition, status=PROVISIONAL)
    edition.edition_type = CardEditionType.MOMENT
    db.commit()

    result = publish_card_catalog(
        db, season=2026, card_edition_id=edition.id,
        rating_model_version="ratings-2.0", data_end_date=END,
    )

    assert result.status == "FAILED"
    assert db.query(PlayerCardModel).count() == 0
    assert any("sólo está implementada para edición BASE" in issue for issue in result.issues)
