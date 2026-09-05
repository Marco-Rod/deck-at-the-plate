"""Pruebas del pipeline raw Statcast: idempotencia, hash, rechazos y DataImportRun (spec 19-22)."""

import pathlib

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.enums import ImportStatus
from app.database import Base
from app.models import DataImportRun, RawPitchEvent
from etl.http.client import ExternalHttpClient
from etl.pipelines.statcast import StatcastRawPipeline
from etl.sources.statcast import StatcastSourceAdapter

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _adapter(csv_text: str):
    def handler(request):
        return httpx.Response(200, text=csv_text, request=request)

    return StatcastSourceAdapter(
        http=ExternalHttpClient(transport=httpx.MockTransport(handler)),
        base_url="https://savant.test",
    )


def _fixture_rows() -> str:
    return (FIXTURES / "statcast_small.csv").read_text()


def _run_pipeline(db, *, adapter=None, refresh=False):
    pipeline = StatcastRawPipeline(db, adapter or _adapter(_fixture_rows()), chunk_days=10)
    from datetime import date

    return pipeline.run(date_from=date(2026, 4, 1), date_to=date(2026, 4, 7), refresh=refresh)


class TestIdempotencia:
    def test_primera_ejecucion_inserta(self, db):
        result = _run_pipeline(db)
        assert result.rows_extracted == 7
        assert result.rows_inserted == 7
        assert result.rows_updated == 0
        assert result.rows_unchanged == 0
        assert result.import_run_id

        event = db.query(RawPitchEvent).filter_by(game_pk=716180, at_bat_number=1, pitch_number=1).one()
        assert event.pitch_family is not None
        assert event.game_zone is not None
        assert db.query(RawPitchEvent).count() == 7

    def test_segunda_ejecucion_no_duplica(self, db):
        _run_pipeline(db)
        result = _run_pipeline(db)
        assert db.query(RawPitchEvent).count() == 7
        assert result.rows_inserted == 0
        assert result.rows_updated == 0
        assert result.rows_unchanged == 7

    def test_hash_same_no_cambia_nada(self, db):
        _run_pipeline(db)
        first = db.query(RawPitchEvent).filter_by(game_pk=716180, at_bat_number=1, pitch_number=1).one()
        result = _run_pipeline(db)
        after = db.query(RawPitchEvent).filter_by(game_pk=716180, at_bat_number=1, pitch_number=1).one()
        assert result.rows_unchanged == 7
        assert after.raw_payload_hash == first.raw_payload_hash


class TestUpdatePorHash:
    def test_hash_distinto_actualiza_en_vez_de_duplicar(self, db):
        _run_pipeline(db)
        first = db.query(RawPitchEvent).filter_by(game_pk=716180, at_bat_number=1, pitch_number=1).one()
        old_hash = first.raw_payload_hash

        mutable = _fixture_rows().replace("FF,98.2,2400", "FF,98.3,2400", 1)
        pipeline = StatcastRawPipeline(
            db,
            _adapter(mutable),
            chunk_days=10,
        )
        from datetime import date

        result = pipeline.run(date_from=date(2026, 4, 1), date_to=date(2026, 4, 7))
        # solo cambió el payload del primer pitch (velocidad) → 1 update
        assert result.rows_updated == 1
        assert result.rows_unchanged == 6
        after = db.query(RawPitchEvent).filter_by(game_pk=716180, at_bat_number=1, pitch_number=1).one()
        assert after.raw_payload_hash != old_hash


class TestRechazosYCounters:
    def test_fila_invalida_aumenta_rows_rejected_y_no_se_inserta(self, db):
        bad = _fixture_rows().replace("716180,2026-04-01,1,1,", "716180,2026-04-01,0,1,", 1)
        pipeline = StatcastRawPipeline(db, _adapter(bad), chunk_days=10)
        from datetime import date

        result = pipeline.run(date_from=date(2026, 4, 1), date_to=date(2026, 4, 7))
        assert result.rows_rejected == 1
        assert result.rows_inserted == 6
        assert db.query(RawPitchEvent).count() == 6
        raw_run = db.query(DataImportRun).order_by(DataImportRun.started_at.desc()).first()
        assert raw_run.rows_rejected == 1
        assert raw_run.rows_inserted == 6

    def test_data_import_run_success(self, db):
        _run_pipeline(db)
        raw_run = db.query(DataImportRun).one()
        assert raw_run.status == ImportStatus.SUCCESS
        assert raw_run.source == "STATCAST"
        assert raw_run.pipeline_version
        assert raw_run.rows_extracted == 7
        assert raw_run.rows_inserted == 7
        assert raw_run.finished_at is not None

    def test_fallo_http_queda_failed_con_error_summary(self, db):
        def handler(request):
            return httpx.Response(500, request=request)

        adapter = StatcastSourceAdapter(
            http=ExternalHttpClient(transport=httpx.MockTransport(handler)),
            base_url="https://savant.test",
        )
        pipeline = StatcastRawPipeline(db, adapter, chunk_days=10)
        from datetime import date

        result = pipeline.run(date_from=date(2026, 4, 1), date_to=date(2026, 4, 7))
        assert result.rows_extracted == 0
        raw_run = db.query(DataImportRun).one()
        assert raw_run.status == ImportStatus.FAILED
        assert raw_run.error_summary
        assert db.query(RawPitchEvent).count() == 0


class TestRefreshMode:
    def test_refresh_actualiza_aunque_hash_igual(self, db):
        _run_pipeline(db)
        result = _run_pipeline(db, refresh=True)
        assert result.rows_updated == 7
        assert db.query(RawPitchEvent).count() == 7