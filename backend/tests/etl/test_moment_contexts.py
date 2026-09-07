"""MomentContext persiste hechos reproducibles sin interpretación de juego."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    MomentContext,
    MomentContextSourceType,
    Player,
)
from etl.services.moment_contexts import (
    MOMENT_CONTEXT_VERSION,
    persist_moment_context,
)


OCCURRED_AT = dt.datetime(2026, 9, 5, 21, 15, tzinfo=dt.timezone.utc)
FACTS = {
    "game": {
        "game_pk": 824230,
        "opponent": "PHI",
        "team_runs": 5,
        "opponent_runs": 4,
    },
    "batting": {
        "plate_appearances": 5,
        "at_bats": 5,
        "hits": 4,
        "home_runs": 2,
        "runs_batted_in": 5,
        "walk_off": True,
    },
}


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _player(db, mlb_id=660271):
    player = Player(mlb_id=mlb_id, full_name=f"Player {mlb_id}")
    db.add(player)
    db.flush()
    return player


def _edition(db, *, edition_type=CardEditionType.MOMENT, code="2026_MOMENT_001"):
    edition = CardEdition(
        code=code,
        name="Walk-Off Hero",
        edition_type=edition_type,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference="mlb-game:824230",
        metadata_payload={"game_pk": 824230},
    )
    db.add(edition)
    db.flush()
    return edition


def _persist(db, player, edition, **overrides):
    values = {
        "player_id": player.id,
        "card_edition_id": edition.id,
        "role": "BATTER",
        "occurred_at": OCCURRED_AT,
        "source_type": MomentContextSourceType.STATCAST,
        "source_reference": "statcast:824230:660271",
        "facts": FACTS,
    }
    values.update(overrides)
    return persist_moment_context(db, **values)


def test_persiste_hechos_y_provenance_sin_evaluarlos(db):
    player = _player(db)
    edition = _edition(db)
    db.commit()

    result = _persist(db, player, edition)
    context = db.get(MomentContext, result.moment_context_id)

    assert result.status == "CREATED"
    assert context.player_id == player.id
    assert context.card_edition_id == edition.id
    assert context.role == "BATTER"
    assert context.season == 2026
    assert context.context_version == MOMENT_CONTEXT_VERSION
    assert context.source_type == MomentContextSourceType.STATCAST
    assert context.facts["batting"]["walk_off"] is True
    assert len(context.input_hash) == 64


def test_misma_entrada_es_unchanged_y_conserva_uuid(db):
    player = _player(db)
    edition = _edition(db)
    db.commit()

    created = _persist(db, player, edition)
    unchanged = _persist(db, player, edition)

    assert unchanged.status == "UNCHANGED"
    assert unchanged.moment_context_id == created.moment_context_id
    assert unchanged.input_hash == created.input_hash
    assert db.query(MomentContext).count() == 1


def test_cambio_factual_actualiza_el_mismo_contexto(db):
    player = _player(db)
    edition = _edition(db)
    db.commit()
    created = _persist(db, player, edition)

    corrected_facts = {
        **FACTS,
        "batting": {**FACTS["batting"], "runs_batted_in": 6},
    }
    updated = _persist(db, player, edition, facts=corrected_facts)
    context = db.get(MomentContext, created.moment_context_id)

    assert updated.status == "UPDATED"
    assert updated.moment_context_id == created.moment_context_id
    assert updated.input_hash != created.input_hash
    assert context.facts["batting"]["runs_batted_in"] == 6


def test_misma_edicion_admite_contextos_de_jugadores_distintos(db):
    first_player = _player(db)
    second_player = _player(db, mlb_id=650911)
    edition = _edition(db)
    db.commit()

    first = _persist(db, first_player, edition)
    second = _persist(
        db,
        second_player,
        edition,
        role="PITCHER",
        source_reference="statcast:824230:650911",
        facts={
            "game": {"game_pk": 824230},
            "pitching": {
                "pitches": 101,
                "outs_recorded": 27,
                "strikeouts": 12,
                "hits_allowed": 0,
            },
        },
    )

    assert first.moment_context_id != second.moment_context_id
    assert db.query(MomentContext).count() == 2


def test_rechaza_edicion_que_no_sea_moment(db):
    player = _player(db)
    edition = _edition(db, edition_type=CardEditionType.BASE, code="2026_BASE")
    db.commit()

    with pytest.raises(ValueError, match="edición MOMENT"):
        _persist(db, player, edition)


@pytest.mark.parametrize(
    "facts, message",
    [
        ({}, "objeto no vacío"),
        ({"significance": "HIGH"}, "capa interpretativa"),
        ({"batting": {"boosts": {"power": 10}}}, "capa interpretativa"),
        ({"ratings": {"power": 90}}, "capa interpretativa"),
    ],
)
def test_rechaza_resultados_interpretativos_en_facts(db, facts, message):
    player = _player(db)
    edition = _edition(db)
    db.commit()

    with pytest.raises(ValueError, match=message):
        _persist(db, player, edition, facts=facts)


def test_modelo_no_contiene_evaluacion_ratings_ni_rarity():
    columns = set(MomentContext.__table__.columns.keys())
    assert "significance" not in columns
    assert "rating_adjustments" not in columns
    assert "ratings" not in columns
    assert "rarity" not in columns
