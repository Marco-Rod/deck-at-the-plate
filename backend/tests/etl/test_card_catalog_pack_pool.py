"""validate_pack_pool exige catálogo ACTIVE, cartas elegibles y pool por rarity."""

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
from etl.services.card_catalog import validate_pack_pool

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


def _edition(db):
    edition = CardEdition(
        code="2026_BASE",
        name="Base",
        edition_type=CardEditionType.BASE,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.SYSTEM,
        metadata_payload={},
    )
    db.add(edition)
    db.flush()
    return edition


def _catalog(db, *, status="ACTIVE"):
    catalog = CardCatalog(
        season=2026,
        edition_type="BASE",
        version=1,
        status=status,
    )
    db.add(catalog)
    db.flush()
    return catalog


def _card(db, catalog, edition, *, rarity, eligible=True):
    card = PlayerCardModel(
        id=f"{rarity.value}-{catalog.id}-{eligible}",
        name=f"Card {rarity.value}",
        position="DH",
        overall=70,
        rarity=rarity,
        vision=50,
        clutch=50,
        is_pack_eligible=eligible,
        is_active=True,
        card_edition_id=edition.id,
        catalog_id=catalog.id,
    )
    db.add(card)
    db.flush()
    return card


def test_pool_completo_de_los_cinco_tiers(db):
    edition = _edition(db)
    catalog = _catalog(db)
    for rarity in RARITIES:
        _card(db, catalog, edition, rarity=rarity)

    result = validate_pack_pool(db, season=2026)

    assert result.ok
    assert any("COMMON=1; BRONZE=1; SILVER=1; GOLD=1; DIAMOND=1" in line for line in result.detail)


def test_missing_rarity_reporta_gap(db):
    edition = _edition(db)
    catalog = _catalog(db)
    for rarity in RARITIES[:-1]:
        _card(db, catalog, edition, rarity=rarity)

    result = validate_pack_pool(db, season=2026)

    assert not result.ok
    assert any("sin cartas elegibles para DIAMOND" in line for line in result.detail)


def test_required_rarities_personalizadas(db):
    edition = _edition(db)
    catalog = _catalog(db)
    _card(db, catalog, edition, rarity=CardRarity.COMMON)
    _card(db, catalog, edition, rarity=CardRarity.GOLD)

    result = validate_pack_pool(
        db, season=2026, required_rarities=(CardRarity.COMMON, CardRarity.GOLD)
    )

    assert result.ok


def test_cartas_no_elegibles_fallan_el_gate(db):
    edition = _edition(db)
    catalog = _catalog(db)
    for rarity in RARITIES:
        _card(db, catalog, edition, rarity=rarity)
    _card(db, catalog, edition, rarity=CardRarity.COMMON, eligible=False)

    result = validate_pack_pool(db, season=2026)

    assert not result.ok
    assert any("sin is_pack_eligible" in line for line in result.detail)


def test_sin_catalogo_active(db):
    _edition(db)
    _catalog(db, status="RETIRED")

    result = validate_pack_pool(db, season=2026)

    assert not result.ok
    assert result.detail == ["sin catálogo ACTIVE"]