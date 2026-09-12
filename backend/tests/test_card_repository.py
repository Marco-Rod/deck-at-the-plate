"""find_cards_by_rarity solo mira el pool jugable: catálogo ACTIVE y elegible."""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardCatalog,
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    PlayerCardModel,
)
from app.models.card import CardRarity
from app.repositories.card_repository import (
    find_cards_by_rarity,
    get_active_pack_catalog,
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


def _edition(db, *, code, season=2026):
    edition = CardEdition(
        code=code,
        name="Test Edition",
        edition_type=CardEditionType.BASE,
        season=season,
        version="edition-1.0",
        source_type=CardEditionSourceType.SYSTEM,
        metadata_payload={},
    )
    db.add(edition)
    db.flush()
    return edition


def _catalog(db, *, season=2026, status="ACTIVE", edition_type="BASE", version=1):
    catalog = CardCatalog(
        season=season,
        edition_type=edition_type,
        version=version,
        status=status,
    )
    db.add(catalog)
    db.flush()
    return catalog


def _card(db, catalog, edition, *, rarity, eligible=True, card_id):
    card = PlayerCardModel(
        id=card_id,
        name=f"Card {card_id}",
        position="DH",
        overall=70,
        rarity=rarity,
        vision=50,
        clutch=50,
        is_pack_eligible=eligible,
        is_active=True,
        card_edition_id=edition.id,
        catalog_id=catalog.id if catalog is not None else None,
    )
    db.add(card)
    db.flush()
    return card


def test_solo_catalogo_active_y_elegibles(db):
    edition = _edition(db, code="2026_BASE")
    active = _catalog(db)
    retired = _catalog(db, status="RETIRED", edition_type="TEAM_STAR")
    active_common = _card(db, active, edition, rarity=CardRarity.COMMON, card_id="active-common")
    _card(db, active, edition, rarity=CardRarity.COMMON, card_id="active-noneligible", eligible=False)
    _card(db, retired, edition, rarity=CardRarity.COMMON, card_id="retired-common")
    _card(db, None, edition, rarity=CardRarity.COMMON, card_id="seed-common")

    result = find_cards_by_rarity(db, CardRarity.COMMON)

    assert [c.id for c in result] == ["active-common"]


def test_filtra_por_rarity(db):
    edition = _edition(db, code="2026_BASE")
    active = _catalog(db)
    _card(db, active, edition, rarity=CardRarity.COMMON, card_id="common-1")
    _card(db, active, edition, rarity=CardRarity.GOLD, card_id="gold-1")
    _card(db, active, edition, rarity=CardRarity.GOLD, card_id="gold-2")

    assert {c.id for c in find_cards_by_rarity(db, CardRarity.GOLD)} == {"gold-1", "gold-2"}
    assert {c.id for c in find_cards_by_rarity(db, CardRarity.COMMON)} == {"common-1"}


def test_catalog_id_restringe_a_esa_edicion(db):
    edition = _edition(db, code="2026_BASE")
    catalog_a = _catalog(db, season=2026)
    catalog_b = _catalog(db, season=2027, version=1)
    _card(db, catalog_a, edition, rarity=CardRarity.SILVER, card_id="silver-a")
    _card(db, catalog_b, edition, rarity=CardRarity.SILVER, card_id="silver-b")

    result = find_cards_by_rarity(db, CardRarity.SILVER, catalog_id=catalog_a.id)

    assert [c.id for c in result] == ["silver-a"]


def test_pack_catalog_determinista_por_season(db):
    _edition(db, code="2026_BASE")
    base_2026 = _catalog(db, season=2026, version=1)
    base_2025 = _catalog(db, season=2025, version=1)
    team_star_2026 = _catalog(db, season=2026, edition_type="TEAM_STAR", version=1)

    # El único BASE ACTIVE de 2026 gana sobre el ACTIVE de 2025 (season mandó).
    assert get_active_pack_catalog(db, season=2026).id == base_2026.id
    assert get_active_pack_catalog(db).id == base_2026.id
    assert get_active_pack_catalog(db, season=2026, edition_type="BASE") != base_2025
    # edition_type aislado: solo resuelve el ACTIVE de ese tipo.
    assert (
        get_active_pack_catalog(db, season=2026, edition_type="TEAM_STAR").id
        == team_star_2026.id
    )