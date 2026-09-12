"""open_pack: pool fijo a UN catálogo ACTIVE; sin fallback a legacy/semillas."""

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
    User,
    UserCardInventory,
    UserWallet,
)
from app.models.card import CardRarity
from app.repositories.card_repository import count_user_inventory, find_cards_by_rarity
from app.services.pack_service import PackPoolError, PackService

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


class FakeRandom:
    """Fuerza rareza y posición deterministas en open_pack."""

    def __init__(self, rarity):
        self._rarity = rarity

    def choices(self, population, weights=None, k=1):
        return [self._rarity]

    def choice(self, population):
        return population[0]


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


def _catalog(db, *, season, status="ACTIVE", edition_type="BASE"):
    catalog = CardCatalog(
        season=season,
        edition_type=edition_type,
        version=1,
        status=status,
    )
    db.add(catalog)
    db.flush()
    return catalog


def _card(db, catalog, edition, *, rarity, card_id, eligible=True):
    card = PlayerCardModel(
        id=card_id,
        name=card_id,
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


def _user_with_wallet(db, stamps):
    user = User(username=f"user-{stamps}", hashed_password="x")
    db.add(user)
    db.flush()
    wallet = UserWallet(user_id=user.id, stamps=stamps, gems=0)
    db.add(wallet)
    db.flush()
    return user


def test_sobre_fija_catalogo_y_nunca_mezcla_ediciones(db, monkeypatch):
    monkeypatch.setattr("app.services.pack_service.random", FakeRandom(CardRarity.COMMON))
    edition = _edition(db)
    catalog_a = _catalog(db, season=2026)
    catalog_b = _catalog(db, season=2027)
    for rarity in (CardRarity.COMMON, CardRarity.BRONZE, CardRarity.SILVER):
        _card(db, catalog_a, edition, rarity=rarity, card_id=f"a-{rarity.value}")
        _card(db, catalog_b, edition, rarity=rarity, card_id=f"b-{rarity.value}")
    user = _user_with_wallet(db, stamps=2000)

    pulled = PackService.open_pack(db, user_id=user.id, pack_type="BRONZE", season=2026)

    assert len(pulled) == 3
    assert {p.id for p in pulled} == {"a-COMMON"}
    assert count_user_inventory(db, user.id) == 3
    stored = [row.card_id for row in db.query(UserCardInventory).all()]
    assert set(stored) == {"a-COMMON"}


def test_tier_sin_pool_aborta_antes_de_cobrar(db):
    edition = _edition(db)
    catalog = _catalog(db, season=2026)
    _card(db, catalog, edition, rarity=CardRarity.COMMON, card_id="only-common")
    user = _user_with_wallet(db, stamps=1500)

    with pytest.raises(PackPoolError):
        PackService.open_pack(db, user_id=user.id, pack_type="GOLD", season=2026)

    wallet = db.query(UserWallet).filter_by(user_id=user.id).one()
    assert wallet.stamps == 1500
    assert count_user_inventory(db, user.id) == 0


def test_seed_y_retirados_jamas_cubren_el_gap_de_pool(db, monkeypatch):
    monkeypatch.setattr("app.services.pack_service.random", FakeRandom(CardRarity.GOLD))
    edition = _edition(db)
    catalog = _catalog(db, season=2026)
    _card(db, catalog, edition, rarity=CardRarity.COMMON, card_id="only-common")
    _card(db, None, edition, rarity=CardRarity.GOLD, card_id="seed-gold")
    retired = _catalog(db, season=2026, status="RETIRED", edition_type="TEAM_STAR")
    _card(db, retired, edition, rarity=CardRarity.GOLD, card_id="retired-gold")

    assert find_cards_by_rarity(db, CardRarity.GOLD) == []
    user = _user_with_wallet(db, stamps=4000)
    with pytest.raises(PackPoolError) as excinfo:
        PackService.open_pack(db, user_id=user.id, pack_type="DIAMOND", season=2026)

    assert "pool sin cartas elegibles" in excinfo.value.detail
    assert "SILVER" in excinfo.value.detail or "GOLD" in excinfo.value.detail or "DIAMOND" in excinfo.value.detail
    wallet = db.query(UserWallet).filter_by(user_id=user.id).one()
    assert wallet.stamps == 4000
    assert count_user_inventory(db, user.id) == 0


def test_catalog_id_explicito_de_otro_edition_type_se_rechaza(db):
    edition = _edition(db)
    moment = _catalog(db, season=2026, edition_type="MOMENT")
    _card(db, moment, edition, rarity=CardRarity.COMMON, card_id="moment-common")
    user = _user_with_wallet(db, stamps=1500)

    with pytest.raises(PackPoolError) as excinfo:
        PackService.open_pack(
            db, user_id=user.id, pack_type="BRONZE", catalog_id=moment.id
        )

    assert "no es de tipo BASE" in excinfo.value.detail
    wallet = db.query(UserWallet).filter_by(user_id=user.id).one()
    assert wallet.stamps == 1500