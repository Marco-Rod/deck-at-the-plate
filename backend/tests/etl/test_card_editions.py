"""Contrato de identidad y provenance de CardEdition."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CardEdition, CardEditionSourceType, CardEditionType


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _edition(**overrides):
    values = {
        "code": "2026_BASE",
        "name": "2026 Base Set",
        "edition_type": CardEditionType.BASE,
        "season": 2026,
        "version": "edition-1.0",
        "is_active": True,
        "source_type": CardEditionSourceType.SYSTEM,
        "metadata_payload": {},
    }
    values.update(overrides)
    return CardEdition(**values)


def test_persiste_identidad_versionada_y_provenance(db):
    starts_at = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)
    ends_at = dt.datetime(2026, 7, 31, tzinfo=dt.timezone.utc)
    edition = _edition(
        code="2026_ALL_STAR",
        name="2026 All-Star",
        edition_type=CardEditionType.ALL_STAR,
        source_type=CardEditionSourceType.EVENT,
        source_reference="mlb:all-star-game:2026",
        starts_at=starts_at,
        ends_at=ends_at,
        metadata_payload={"event": "ALL_STAR_GAME", "venue": "Philadelphia"},
    )
    db.add(edition)
    db.commit()

    assert edition.id is not None
    assert edition.edition_type == CardEditionType.ALL_STAR
    assert edition.source_type == CardEditionSourceType.EVENT
    assert edition.source_reference == "mlb:all-star-game:2026"
    assert edition.metadata_payload["event"] == "ALL_STAR_GAME"
    assert edition.created_at is not None
    assert edition.updated_at is not None


def test_tipos_de_edicion_validos(db):
    for index, edition_type in enumerate(CardEditionType):
        db.add(_edition(
            code=f"2026_{edition_type.value}",
            name=edition_type.value,
            edition_type=edition_type,
        ))
    db.commit()
    assert db.query(CardEdition).count() == len(CardEditionType)


def test_code_es_unico_por_temporada_y_version(db):
    db.add(_edition())
    db.commit()
    db.add(_edition(name="Duplicada"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    db.add(_edition(version="edition-2.0", name="Nueva metodología"))
    db.add(_edition(season=2027, name="Otra temporada"))
    db.commit()
    assert db.query(CardEdition).count() == 3


def test_ventana_temporal_es_opcional_y_ordenada(db):
    db.add(_edition(code="NO_WINDOW", starts_at=None, ends_at=None))
    db.commit()

    db.add(_edition(
        code="BAD_WINDOW",
        starts_at=dt.datetime(2026, 8, 2),
        ends_at=dt.datetime(2026, 8, 1),
    ))
    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize("field", ["edition_type", "source_type"])
def test_rechaza_tipos_fuera_del_dominio(db, field):
    edition = _edition(**{field: "NOT_A_REAL_TYPE"})
    db.add(edition)
    with pytest.raises(StatementError):
        db.flush()


def test_no_contiene_rarity_ni_boosts():
    columns = set(CardEdition.__table__.columns.keys())
    assert "rarity" not in columns
    assert "rating_boost" not in columns
    assert "boosts" not in columns
