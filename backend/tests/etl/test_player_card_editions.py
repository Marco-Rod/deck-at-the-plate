"""Identidad Player + CardEdition y publicación idempotente."""

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
    CardGenerationProfile,
    GamePlayerIdentity,
    Player,
    PlayerCardModel,
    PlayerSeason,
    SourceTeam,
    SourceTeamGameTeamMapping,
    SourceTeamRosterMember,
    SourceTeamRosterSnapshot,
    Team,
)
from app.models.card import CardRarity
from app.services.card_editions import ensure_system_base_edition
from etl.services.base_eligibility_policy import BASE_ELIGIBILITY_POLICY_VERSION
from etl.services.card_catalog import publish_card_catalog


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


def _edition(db, code, edition_type):
    edition = CardEdition(
        code=code,
        name=code,
        edition_type=edition_type,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.SYSTEM,
        metadata_payload={},
    )
    db.add(edition)
    db.flush()
    return edition


def _player(db, mlb_id):
    player = Player(
        mlb_id=mlb_id,
        full_name=f"Player {mlb_id}",
        primary_position="DH",
    )
    db.add(player)
    db.flush()
    return player


def _card(player, edition, card_id):
    return PlayerCardModel(
        id=card_id,
        name=card_id,
        position="DH",
        overall=70,
        player_id=player.id,
        season=2026,
        card_edition_id=edition.id,
    )


def test_identidad_permite_multiples_ediciones_y_jugadores(db):
    base = _edition(db, "2026_BASE", CardEditionType.BASE)
    all_star = _edition(db, "2026_ALL_STAR", CardEditionType.ALL_STAR)
    ohtani = _player(db, 660271)
    judge = _player(db, 592450)
    db.add_all([
        _card(ohtani, base, "ohtani-base"),
        _card(ohtani, all_star, "ohtani-all-star"),
        _card(judge, base, "judge-base"),
    ])
    db.commit()

    assert db.query(PlayerCardModel).count() == 3
    assert {card.card_edition.code for card in ohtani_cards(db, ohtani.id)} == {
        "2026_BASE",
        "2026_ALL_STAR",
    }


def ohtani_cards(db, player_id):
    return db.query(PlayerCardModel).filter_by(player_id=player_id).all()


def test_mismo_jugador_y_edicion_no_duplica(db):
    edition = _edition(db, "2026_BASE", CardEditionType.BASE)
    player = _player(db, 660271)
    db.add(_card(player, edition, "first"))
    db.commit()
    db.add(_card(player, edition, "duplicate"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_card_edition_inexistente_falla_fk(db):
    db.add(PlayerCardModel(
        id="orphan-card",
        name="Orphan",
        position="DH",
        overall=70,
        card_edition_id="missing-edition",
    ))
    with pytest.raises(IntegrityError):
        db.flush()


def test_edicion_base_explicita_es_idempotente(db):
    first = ensure_system_base_edition(db, season=2026)
    db.commit()
    second = ensure_system_base_edition(db, season=2026)
    assert second.id == first.id
    assert second.code == "2026_BASE"
    assert second.version == "edition-1.0"
    assert second.eligibility_policy_version == BASE_ELIGIBILITY_POLICY_VERSION
    assert db.query(CardEdition).count() == 1


def test_edicion_base_legacy_no_recibe_backfill_de_eligibility(db):
    legacy = CardEdition(
        code="2025_BASE",
        name="2025 Base Set",
        edition_type=CardEditionType.BASE,
        season=2025,
        version="edition-1.0",
        source_type=CardEditionSourceType.SYSTEM,
        rating_policy_version="base-card-ratings-1.0",
        metadata_payload={"fixture": "legacy"},
    )
    db.add(legacy)
    db.commit()

    resolved = ensure_system_base_edition(db, season=2025)

    assert resolved.id == legacy.id
    assert resolved.eligibility_policy_version is None


def test_rerun_del_publicador_no_duplica_carta(db):
    team = Team(
        id="team-1",
        abbreviation="TST",
        name="Test Team",
        city="Test City",
    )
    source_team = SourceTeam(
        source="MLB",
        external_id=1,
        source_name="Source Team",
        source_abbreviation="SRC",
    )
    player = _player(db, 660271)
    db.add_all([team, source_team])
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
    db.add(CardGenerationProfile(
        player_season_id=player_season.id,
        rating_model_version="ratings-1.0",
        contact_rating=70,
        power_rating=70,
        vision_rating=70,
        clutch_rating=70,
        velocity_rating=0,
        control_rating=0,
        movement_rating=0,
        overall_rating=70,
        calculated_rarity=CardRarity.COMMON,
        calculation_metadata={},
    ))
    edition = ensure_system_base_edition(db, season=2026)
    db.commit()

    first = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-1.0",
        data_end_date=END,
    )
    card = db.query(PlayerCardModel).one()
    card_id = card.id
    second = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-1.0",
        data_end_date=END,
    )

    assert first.status == second.status == "ACTIVE"
    assert first.created == second.created == 1
    assert db.query(PlayerCardModel).count() == 1
    assert db.query(PlayerCardModel).one().id == card_id
    assert db.query(PlayerCardModel).one().card_edition_id == edition.id
