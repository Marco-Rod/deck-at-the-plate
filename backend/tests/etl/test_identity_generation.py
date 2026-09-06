"""Tests del servicio de identidades GAME v2.1 (§72, §80, §83, §85).

Cubre: persistencia gana, dry-run sin escrituras, validación y una integración
de 300 identidades únicas con rerun estable.
"""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import GamePlayerIdentity, PlayerSeason
from etl.dto import PlayerSourceRecord
from etl.loaders.core import upsert_player
from etl.services.identity_generation import (
    generate_identity_batch,
    render_report,
    validate_game_identities,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _player(db, mlb_id, first, last):
    player = upsert_player(
        db,
        PlayerSourceRecord(mlb_id=mlb_id, full_name=f"{first} {last}", first_name=first, last_name=last),
    )
    db.commit()
    return player


def test_persistencia_gana_y_rerun_estable(db):
    player = _player(db, 660271, "Shohei", "Ohtani")
    first = generate_identity_batch(db, missing_only=True)
    assert first.created == 1
    identity = db.query(GamePlayerIdentity).one()
    assert identity.player_id == player.id
    assert identity.display_name != "Shohei Ohtani"
    assert identity.name_profile in ("UNKNOWN", "JAPANESE")
    assert identity.generator_version == "names-1.0"

    second = generate_identity_batch(db, missing_only=True)
    assert second.created == 0
    assert second.unchanged == 1
    assert db.query(GamePlayerIdentity).count() == 1
    assert db.query(GamePlayerIdentity).one().display_name == identity.display_name


def test_dry_run_no_escribe_pero_reporta(db):
    _player(db, 660272, "Jose", "Ramirez")
    result = generate_identity_batch(db, missing_only=True, dry_run=True)
    assert result.dry_run is True
    assert result.created == 0
    assert len(result.report) == 1
    assert db.query(GamePlayerIdentity).count() == 0
    header = render_report(result)
    assert "QA report" in header
    assert "Ramirez" in header

    real = generate_identity_batch(db, missing_only=True)
    assert real.created == 1
    assert db.query(GamePlayerIdentity).count() == 1


def test_validate_ok_tras_generacion(db):
    _player(db, 660273, "Francois", "Dupont")
    generate_identity_batch(db, missing_only=True)
    result = validate_game_identities(db)
    assert result.ok is True
    assert result.detail == []


def test_validate_detecta_identidad_faltante(db):
    _player(db, 660274, "Wei", "Wang")
    result = validate_game_identities(db)
    assert result.ok is False
    assert any("sin identidad" in issue for issue in result.detail)


def test_player_id_filtra_batch(db):
    p1 = _player(db, 1111, "John", "Smith")
    _player(db, 1112, "Jose", "Ramirez")
    result = generate_identity_batch(db, missing_only=True, player_id=1111, limit=1)
    assert result.created == 1
    identity = db.query(GamePlayerIdentity).one()
    assert identity.player_id == p1.id


def test_season_sin_rosters_no_elige_a_nadie(db):
    _player(db, 660276, "Shohei", "Ohtani")
    result = generate_identity_batch(db, missing_only=True, season=2026)
    assert result.created == 0
    assert db.query(GamePlayerIdentity).count() == 0

    with_roster = generate_identity_batch(db, missing_only=True)
    assert with_roster.created == 1
    assert db.query(GamePlayerIdentity).count() == 1


def test_season_con_rosters_filtra_por_temporada(db):
    player = _player(db, 660277, "Jose", "Ramirez")
    db.add(
        PlayerSeason(
            player_id=player.id,
            season=2026,
            data_start_date=date(2026, 3, 1),
            data_end_date=date(2026, 9, 30),
            games=40,
            plate_appearances=170,
            batters_faced=0,
            outs_recorded=0,
        )
    )
    db.commit()
    result = generate_identity_batch(db, missing_only=True, season=2026)
    assert result.created == 1
    identity = db.query(GamePlayerIdentity).one()
    assert identity.player_id == player.id


def test_validacion_season_sin_rosters_ok(db):
    _player(db, 660278, "Wei", "Wang")
    result = validate_game_identities(db, season=2026)
    assert result.ok is True
    assert result.detail == []
    p = _player(db, 660275, "Taylor", "Swiftfied")
    identity = GamePlayerIdentity(
        player_id=p.id,
        display_first_name="Taylor",
        display_last_name="Swiftfied",
        display_name="Taylor Swiftfied",
        name_profile="ENGLISH",
        generator_version="names-1.0",
    )
    db.add(identity)
    db.commit()
    result = validate_game_identities(db)
    assert result.ok is False
    assert any("coincide con nombre fuente" in issue for issue in result.detail)


SURNAMES = ["Ramirez", "Kim", "Wang", "Smith", "Yamamoto", "Muller", "Kovalenko", "Dupont", "De Vries", "Bell"]
GIVEN = ["Jose", "Minjae", "Wei", "John", "Haruto", "Lukas", "Petr", "Luc", "Jan", "Marcus"]


def test_integracion_300_identidades_unicas_y_estables(db):
    for i in range(300):
        first = GIVEN[i % len(GIVEN)]
        last = SURNAMES[i % len(SURNAMES)]
        _player(db, 2000 + i, first, last)

    result = generate_identity_batch(db, missing_only=True)
    assert result.created == 300

    rows = db.query(GamePlayerIdentity).all()
    assert len(rows) == 300
    displays = [r.display_name for r in rows]
    assert len(set(displays)) == 300
    assert all(r.generator_version == "names-1.0" for r in rows)
    assert all(r.name_profile and r.name_profile != "" for r in rows)
    assert all(r.display_name != f"{r.player.first_name} {r.player.last_name}" for r in rows)

    validation = validate_game_identities(db)
    assert validation.ok is True, validation.detail

    rerun = generate_identity_batch(db, missing_only=True)
    assert rerun.created == 0
    assert rerun.unchanged == 300
    assert db.query(GamePlayerIdentity).count() == 300