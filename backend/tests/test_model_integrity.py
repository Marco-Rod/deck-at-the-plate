"""Pruebas de las restricciones de integridad agregadas en 0008 (cambiosprevisoaletl.md).

Se ejecutan contra sqlite en-memory con el esquema completo. SQLite aplica
UNIQUE, CHECK y NOT NULL en INSERT/UPDATE, por lo que reproducen las reglas de
Postgres sin necesidad del servidor.
"""

import datetime as dt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.core.enums import BatterSide, ImportStatus
from app.core.time import utcnow
from app.models import (
    BatterHandednessSplit,
    BatterPitcherMatchup,
    BatterSeasonStats,
    BatterZoneProfile,
    DataImportRun,
    PitcherHandednessSplit,
    PitcherPitchProfile,
    PitcherSeasonStats,
    PitcherZoneProfile,
    Player,
    PlayerSeason,
    PlayerTeamStint,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _player(db, **overrides):
    p = Player(
        mlb_id=1,
        full_name="Jugador Test",
        first_name="Jugador",
        last_name="Test",
        **overrides,
    )
    db.add(p)
    db.flush()
    return p


def _player_season(db, player=None, **overrides):
    player = player or _player(db)
    ps = PlayerSeason(
        player_id=player.id,
        season=2026,
        data_start_date=dt.date(2026, 3, 20),
        data_end_date=dt.date(2026, 9, 1),
        **overrides,
    )
    db.add(ps)
    db.flush()
    return ps


class TestPlayerTeamStint:
    def test_stint_duplicado_rechazado(self, db):
        player = _player(db)
        base = {
            "player_id": player.id,
            "season": 2026,
            "team_id": "LAD",
            "start_date": dt.date(2026, 4, 1),
        }
        db.add(PlayerTeamStint(**base))
        db.flush()
        db.add(PlayerTeamStint(**{**base, "end_date": dt.date(2026, 6, 1)}))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_end_date_antes_de_start_date_rechazado(self, db):
        player = _player(db)
        db.add(PlayerTeamStint(
            player_id=player.id,
            season=2026,
            team_id="LAD",
            start_date=dt.date(2026, 6, 1),
            end_date=dt.date(2026, 4, 1),
        ))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_stint_abierto_con_end_date_nulo_es_valido(self, db):
        player = _player(db)
        stint = PlayerTeamStint(
            player_id=player.id,
            season=2026,
            team_id="LAD",
            start_date=dt.date(2026, 4, 1),
            end_date=None,
        )
        db.add(stint)
        db.flush()
        assert stint.id is not None


class TestDataImportRun:
    def test_contador_negativo_rechazado(self, db):
        db.add(DataImportRun(
            source="TEST",
            pipeline_version="v1",
            rows_rejected=-1,
        ))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_ventana_fechas_invalida_rechazada(self, db):
        db.add(DataImportRun(
            source="TEST",
            pipeline_version="v1",
            date_from=dt.date(2026, 6, 1),
            date_to=dt.date(2026, 4, 1),
        ))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_ventana_con_extremos_nulos_es_valida(self, db):
        run = DataImportRun(source="TEST", pipeline_version="v1")
        db.add(run)
        db.flush()
        assert run.status == ImportStatus.RUNNING
        assert run.started_at.tzinfo is not None


class TestSampleSizeDenominador:
    def test_batter_zone_profile_sample_size_debe_ser_pitches_seen(self, db):
        ps = _player_season(db)
        db.add(BatterZoneProfile(
            player_season_id=ps.id,
            zone=1,
            pitches_seen=10,
            sample_size=11,
        ))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_pitcher_pitch_profile_requiere_sample_size(self, db):
        ps = _player_season(db)
        db.add(PitcherPitchProfile(
            player_season_id=ps.id,
            pitch_type="FF",
            pitch_count=5,
            usage_rate=0.5,
        ))
        # server_default aplica sample_size=0, vioal 'sample_size = pitch_count'.
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_batter_split_sample_size_debe_ser_pa(self, db):
        ps = _player_season(db)
        db.add(BatterHandednessSplit(
            player_season_id=ps.id,
            pa=7,
            sample_size=8,
        ))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_pitcher_handedness_split_batter_side_usa_batter_side(self, db):
        ps = _player_season(db)
        split = PitcherHandednessSplit(
            player_season_id=ps.id,
            batter_side=BatterSide.LEFT,
            batters_faced=12,
            sample_size=12,
        )
        db.add(split)
        db.flush()
        assert split.batter_side == BatterSide.LEFT


class TestRateRange:
    def test_rate_fuera_de_rango_rechazado(self, db):
        ps = _player_season(db)
        db.add(BatterSeasonStats(
            player_season_id=ps.id,
            swing_rate=1.5,
        ))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_rate_nulo_permitido(self, db):
        ps = _player_season(db)
        stats = PitcherSeasonStats(player_season_id=ps.id, whiff_rate=None)
        db.add(stats)
        db.flush()
        assert stats.whiff_rate is None


class TestAuthenticatedUtcnow:
    def test_utcnow_es_aware(self):
        assert utcnow().tzinfo is not None