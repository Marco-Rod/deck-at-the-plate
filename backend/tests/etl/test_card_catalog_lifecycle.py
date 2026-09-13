"""Lifecycle v1 -> v2 de catálogos BASE: dos fases, promote y retract atómicos.

Modelo fiel al dry-run real: el MISMO roster de jugadores tiene perfiles de
carta (CardRatingProfile) para varias ediciones. Al publicar una edición
nueva, toda la plantilla que resuelve para ella produce cartas del candidato.

Flujo cubierto:
    1. publish E1 (sin ACTIVE previo) -> promoción inmediata (ACTIVE v1).
    2. republish E1 -> no-op POR EDICIÓN (no por season+edition_type).
    3. publish E2 (otra edición, ACTIVE previo) -> candidato VALIDATING v2,
       sin reemplazar al ACTIVE (bug de bloqueo del roadmap).
    4. promote(v2) -> swap atómico: v1 RETIRED con cartas off, v2 ACTIVE con
       cartas on y supersedes_catalog_id=v1.
    5. retract(v2) -> restaura v1 ACTIVE (cadena reversible), v2 RETIRED.
"""

import datetime as dt

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardCatalog,
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
from etl.services.base_eligibility_policy import (
    BASE_ELIGIBILITY_POLICY_VERSION,
    INELIGIBLE,
    PROVISIONAL,
)
from etl.services.card_catalog import (
    promote_card_catalog,
    publish_card_catalog,
    retract_card_catalog,
    validate_cpu_rosters,
    validate_pack_pool,
)
from etl.services.card_rating_policies import BASE_RATING_POLICY_VERSION
from etl.services.card_rating_profiles import generate_card_rating_profile

START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)

RARITIES = (
    CardRarity.COMMON,
    CardRarity.BRONZE,
    CardRarity.SILVER,
    CardRarity.GOLD,
    CardRarity.DIAMOND,
)


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


def _edition(db, *, code):
    edition = CardEdition(
        code=code,
        name=f"Base {code}",
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


def _publication_player(db, editions, *, index, rarity, ineligible_for=None):
    """Jugador con perfiles de carta (y eligibility materializada) para las
    ediciones dadas. Si ineligible_for == ed, esa edición lo declara
    INELIGIBLE (no aporta carta al catálogo de esa edición)."""
    team = Team(
        id=f"team-{index}",
        abbreviation=f"T{index}",
        name=f"Test Team {index}",
        city="Test City",
    )
    source_team = SourceTeam(
        source="MLB",
        external_id=100 + index,
        source_name=f"Source Team {index}",
        source_abbreviation=f"SRC{index}",
    )
    player = Player(mlb_id=600000 + index, full_name=f"Player {index}", primary_position="DH")
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
        display_last_name=f"Player {index}",
        display_name=f"Player {index}",
    ))
    player_season = PlayerSeason(
        player_id=player.id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )
    db.add(player_season)
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
        input_hash=f"a{index}" * 32,
    )
    db.add(ratings)
    db.flush()
    _generation_profile(db, player_season, ratings, rarity=rarity)
    for edition in editions:
        result = generate_card_rating_profile(
            db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
        )
        rating = db.get(CardRatingProfile, result.card_rating_profile_id)
        metadata = dict(rating.metadata_payload or {})
        status = INELIGIBLE if edition is ineligible_for else PROVISIONAL
        metadata["eligibility"] = {
            "policy_version": BASE_ELIGIBILITY_POLICY_VERSION,
            "status": status,
            "reasons": [],
        }
        rating.metadata_payload = metadata
    db.flush()
    return player


def _generation_profile(db, player_season, ratings, *, rarity):
    profile = CardGenerationProfile(
        player_season_id=player_season.id,
        rating_model_version="ratings-2.0",
        role="BATTER",
        player_ratings_id=ratings.id,
        input_hash=f"b{player_season.id}" * 32,
        contact_rating=56,
        power_rating=68,
        vision_rating=66,
        clutch_rating=70,
        velocity_rating=None,
        control_rating=None,
        movement_rating=None,
        stuff_rating=None,
        overall_rating=64,
        calculated_rarity=rarity,
        primary_batter_trait=None,
        primary_pitcher_trait=None,
        repertoire_payload=None,
        calculation_metadata={"adapter_version": "fixture"},
    )
    db.add(profile)
    db.flush()
    return profile


def _publish(db, edition):
    return publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )


def _seed(db, editions, rarities, *, start=1, ineligible_for=None):
    return [
        _publication_player(
            db,
            editions,
            index=start + idx,
            rarity=rarity,
            ineligible_for=ineligible_for,
        )
        for idx, rarity in enumerate(rarities)
    ]


def _actives(db):
    return {c.id for c in db.query(CardCatalog).filter_by(status="ACTIVE")}


def test_publica_otra_edicion_deja_candidato_validating(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    ed2 = _edition(db, code="2026_LIFECYCLE_E2")
    _seed(db, [ed1, ed2], RARITIES)
    db.commit()

    first = _publish(db, ed1)
    v1 = db.get(CardCatalog, first.catalog_id)
    assert first.status == "ACTIVE"
    assert first.created == 5
    assert v1.card_edition_id == ed1.id
    assert v1.published_at is not None

    noop = _publish(db, ed1)
    assert noop.status == "ACTIVE"
    assert noop.catalog_id == v1.id
    assert any("no-op" in issue for issue in noop.issues)

    second = _publish(db, ed2)
    assert second.status == "VALIDATING"
    assert second.created == 5
    v2 = db.get(CardCatalog, second.catalog_id)
    assert second.catalog_id != v1.id
    assert v2.version == 2
    assert v2.card_edition_id == ed2.id
    assert v2.published_at is None
    assert not any("no-op" in issue for issue in second.issues)
    assert _actives(db) == {v1.id}
    assert db.query(PlayerCardModel).filter_by(is_active=True).count() == 5


def test_promote_swap_atomico_v2_active_v1_retired(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    ed2 = _edition(db, code="2026_LIFECYCLE_E2")
    _seed(db, [ed1, ed2], RARITIES)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)
    v2 = db.get(CardCatalog, _publish(db, ed2).catalog_id)
    assert v2.status == "VALIDATING"

    result = promote_card_catalog(db, catalog_id=v2.id)

    v1 = db.get(CardCatalog, v1.id)
    v2 = db.get(CardCatalog, v2.id)
    cards_v1 = db.query(PlayerCardModel).filter_by(catalog_id=v1.id).all()
    cards_v2 = db.query(PlayerCardModel).filter_by(catalog_id=v2.id).all()

    assert result.status == "ACTIVE"
    assert result.created == 5
    assert v1.status == "RETIRED"
    assert v2.status == "ACTIVE"
    assert v2.published_at is not None
    assert v2.supersedes_catalog_id == v1.id
    assert v1.supersedes_catalog_id is None
    assert all(not c.is_active and not c.is_pack_eligible for c in cards_v1)
    assert all(c.is_active and c.is_pack_eligible for c in cards_v2)
    assert _actives(db) == {v2.id}

    pool = validate_pack_pool(db, season=2026)
    assert pool.ok
    assert any(v2.id in line for line in pool.detail)


def test_promote_pool_incompleto_marca_failed_y_conserva_active(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    ed2 = _edition(db, code="2026_LIFECYCLE_E2")
    # El candidato E2 pierde al DIAMOND (INELIGIBLE bajo E2): el pool queda sin
    # ese tier y el gate de promoción debe rechazarlo, conservando el ACTIVE v1.
    _seed(db, [ed1, ed2], RARITIES[:-1])
    _seed(db, [ed1, ed2], (CardRarity.DIAMOND,), start=5, ineligible_for=ed2)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)
    v2 = db.get(CardCatalog, _publish(db, ed2).catalog_id)
    assert v2.status == "VALIDATING"
    assert db.query(PlayerCardModel).filter_by(catalog_id=v2.id).count() == 4

    result = promote_card_catalog(db, catalog_id=v2.id)

    assert result.status == "FAILED"
    assert any("DIAMOND" in issue for issue in result.issues)
    v1 = db.get(CardCatalog, v1.id)
    v2 = db.get(CardCatalog, v2.id)
    assert v1.status == "ACTIVE"
    assert v2.status == "FAILED"
    assert _actives(db) == {v1.id}
    assert db.query(PlayerCardModel).filter_by(is_active=True).count() == 5


def test_promote_noop_cuando_ya_activo(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    _seed(db, [ed1], RARITIES)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)

    result = promote_card_catalog(db, catalog_id=v1.id)

    assert result.status == "ACTIVE"
    assert any("ya ACTIVE (no-op)" in issue for issue in result.issues)
    assert db.get(CardCatalog, v1.id).supersedes_catalog_id is None


def test_promote_requiere_validating(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    ed2 = _edition(db, code="2026_LIFECYCLE_E2")
    _seed(db, [ed1, ed2], RARITIES)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)
    v2 = db.get(CardCatalog, _publish(db, ed2).catalog_id)
    promote_card_catalog(db, catalog_id=v2.id)
    retract_card_catalog(db, catalog_id=v2.id)
    # v2 quedó RETIRED: no es promovible.
    with pytest.raises(ValueError, match="solo un VALIDATING"):
        promote_card_catalog(db, catalog_id=v2.id)
    assert db.get(CardCatalog, v1.id).status == "ACTIVE"


def test_retract_devuelve_active_al_predecesor(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    ed2 = _edition(db, code="2026_LIFECYCLE_E2")
    _seed(db, [ed1, ed2], RARITIES)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)
    v2 = db.get(CardCatalog, _publish(db, ed2).catalog_id)
    promote_card_catalog(db, catalog_id=v2.id)

    result = retract_card_catalog(db, catalog_id=v2.id)

    assert result.status == "ACTIVE"
    assert result.catalog_id == v1.id
    v1 = db.get(CardCatalog, v1.id)
    v2 = db.get(CardCatalog, v2.id)
    assert v1.status == "ACTIVE"
    assert v2.status == "RETIRED"
    cards_v1 = db.query(PlayerCardModel).filter_by(catalog_id=v1.id).all()
    cards_v2 = db.query(PlayerCardModel).filter_by(catalog_id=v2.id).all()
    assert all(c.is_active and c.is_pack_eligible for c in cards_v1)
    assert all(not c.is_active and not c.is_pack_eligible for c in cards_v2)
    assert _actives(db) == {v1.id}
    pool = validate_pack_pool(db, season=2026)
    assert pool.ok
    assert any(v1.id in line for line in pool.detail)


def test_retract_sin_predecesor_falla(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    _seed(db, [ed1], RARITIES)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)

    with pytest.raises(ValueError, match="sin predecesor"):
        retract_card_catalog(db, catalog_id=v1.id)


def test_retract_de_no_active_falla(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    ed2 = _edition(db, code="2026_LIFECYCLE_E2")
    _seed(db, [ed1, ed2], RARITIES)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)
    v2 = db.get(CardCatalog, _publish(db, ed2).catalog_id)
    # v1 nunca fue sustituido: retractar al ACTIVE v1 no tiene cadena que
    # restaurar (aunque exista un VALIDATING en paralelo).
    with pytest.raises(ValueError, match="sin predecesor"):
        retract_card_catalog(db, catalog_id=v1.id)
    promote_card_catalog(db, catalog_id=v2.id)
    # Tras la promoción v1 está RETIRED: ya no es el ACTIVE.
    with pytest.raises(ValueError, match="solo se retracta el ACTIVE"):
        retract_card_catalog(db, catalog_id=v1.id)


def test_validate_pack_pool_candidato_con_catalog_id(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    ed2 = _edition(db, code="2026_LIFECYCLE_E2")
    _seed(db, [ed1, ed2], RARITIES)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)
    v2 = db.get(CardCatalog, _publish(db, ed2).catalog_id)

    as_candidate = validate_pack_pool(
        db, season=2026, catalog_id=v2.id, require_pack_eligible=False
    )
    assert as_candidate.ok
    assert v2.id in as_candidate.detail[0]

    as_default = validate_pack_pool(db, season=2026, catalog_id=v2.id)
    assert not as_default.ok
    assert any("sin is_pack_eligible" in line for line in as_default.detail)

    unknown = validate_pack_pool(db, season=2026, catalog_id="nope")
    assert not unknown.ok
    assert unknown.detail == ["catálogo inexistente: nope"]


def test_validate_cpu_rosters_candidato_con_catalog_id(db):
    ed1 = _edition(db, code="2026_LIFECYCLE_E1")
    _seed(db, [ed1], RARITIES)
    db.commit()
    v1 = db.get(CardCatalog, _publish(db, ed1).catalog_id)

    result = validate_cpu_rosters(db, season=2026, catalog_id=v1.id)
    assert result.ok
    unknown = validate_cpu_rosters(db, season=2026, catalog_id="nope")
    assert not unknown.ok
    assert unknown.detail == ["catálogo inexistente: nope"]