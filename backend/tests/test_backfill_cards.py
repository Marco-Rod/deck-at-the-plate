"""Pruebas del backfill de cartas legacy (vision/clutch/edition/model_version).

Se usa sqlite en-memory con el esquema completo. Las cartas legacy sobreviven
al ALTER con placeholders (vision=50, clutch=50, edition='BASE') porque los
modelos tienen default; el backfill las sobrescribe y las firma con
rating_model_version.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import PlayerCardModel
from app.seeds.backfill_cards import (
    backfill_vision_clutch_edition,
    LEGACY_MODEL_VERSION,
    BASE_EDITION,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _legacy_card(**overrides):
    base = {
        "id": "legacy-1",
        "name": "Legacy Player",
        "team_id": "NYY",
        "position": "SS",
        "overall": 85,
        "contact": 70,
        "power": 75,
        "velocity": 88,
        "control": 84,
        "movement": 82,
    }
    base.update(overrides)
    return PlayerCardModel(**base)


class TestBackfill:
    def test_escribo_valores_y_firma(self, db):
        card = _legacy_card(id="legacy-1")
        db.add(card)
        db.flush()
        # Pre-backfill: placeholders del ALTER (defaults del modelo).
        assert card.vision == 50
        assert card.clutch == 50
        assert card.edition == "BASE"

        summary = backfill_vision_clutch_edition(db)
        assert summary["updated"] == 1

        card = db.query(PlayerCardModel).filter_by(id="legacy-1").one()
        assert card.vision == int(70 * 0.70 + 85 * 0.30)  # 74
        assert card.clutch == 50
        assert card.edition == BASE_EDITION
        assert card.rating_model_version == LEGACY_MODEL_VERSION

    def test_idempotente(self, db):
        card = _legacy_card(id="legacy-2")
        db.add(card)
        db.flush()
        backfill_vision_clutch_edition(db)
        summary = backfill_vision_clutch_edition(db)
        assert summary["updated"] == 0

    def test_no_toca_cartas_ya_backfilleadas(self, db):
        card = _legacy_card(id="legacy-3", rating_model_version="V2", vision=88)
        db.add(card)
        db.flush()
        summary = backfill_vision_clutch_edition(db)
        assert summary["updated"] == 0
        assert db.query(PlayerCardModel).filter_by(id="legacy-3").one().vision == 88