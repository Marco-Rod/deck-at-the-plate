"""Tests de regresión de las correcciones V1.

Referencia: Deck_at_the_Plate_ETL_Corrections_Before_Vertical_Slice_V1.
Cubre: propagación de errores (§1), stop de `run` si RAW falla (§1/§2),
SUCCESS/PARTIAL/FAILED (§5), chunking seguro + subdivisión por umbral (§3),
bulk UPSERT con contadores correctos (§4), resolución de Players desde RAW
sin rosters (§6), y `pipeline_version` central (sin hardcode, §b).
"""

import datetime as dt
import pathlib

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.enums import ImportStatus
from app.database import Base
from app.models import DataImportRun, Player, RawPitchEvent
from etl.config import ETL_PIPELINE_VERSION
from etl.http.client import ExternalHttpClient
from etl.loaders.raw import upsert_raw_pitch_events
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


def _csv_rows() -> str:
    return (FIXTURES / "statcast_small.csv").read_text()


def _adapter(csv_text: str = None, *, threshold: int = 25000, chunk_days: int = 5, log: dict | None = None):
    if csv_text is None:
        csv_text = _csv_rows()

    def handler(request):
        if log is not None:
            log["requests"] = log.get("requests", 0) + 1
        return httpx.Response(200, text=csv_text, request=request)

    return StatcastSourceAdapter(
        http=ExternalHttpClient(transport=httpx.MockTransport(handler)),
        base_url="https://savant.test",
        chunk_days=chunk_days,
        safe_row_threshold=threshold,
    )


def _pipeline(db, *, adapter=None, chunk_days=10):
    return StatcastRawPipeline(db, adapter or _adapter(chunk_days=5), chunk_days=chunk_days)


class TestBulkUpsert:
    """§4: bulk por lotes, probe acotado y contadores correctos."""

    def _row(self, game_pk, at_bat, pitch, speed, *, hash_):
        return {
            "source": "STATCAST",
            "game_pk": game_pk,
            "game_date": dt.date(2026, 4, 1),
            "season": 2026,
            "at_bat_number": at_bat,
            "pitch_number": pitch,
            "batter_mlb_id": 660271,
            "pitcher_mlb_id": 669373,
            "release_speed": speed,
            "raw_payload_hash": hash_,
        }

    def _rows(self):
        return {k: self._row(716180, i, 1, 98.0 + i, hash_=f"h{i}") for i, k in enumerate(("a", "b", "c", "d", "e", "f", "g"))}

    def test_multi_lote_inserta_y_relanza_sin_duplicar(self, db):
        rows = self._rows()
        first = upsert_raw_pitch_events(db, import_run_id="r1", rows=list(rows.values()), batch_size=2)
        assert first.inserted == 7
        assert first.updated == 0
        assert first.unchanged == 0
        assert db.query(RawPitchEvent).count() == 7

        second = upsert_raw_pitch_events(db, import_run_id="r2", rows=list(rows.values()), batch_size=2)
        assert second.inserted == 0
        assert second.updated == 0
        assert second.unchanged == 7
        assert db.query(RawPitchEvent).count() == 7

    def test_cambio_hash_actualiza_no_duplica(self, db):
        rows = self._rows()
        upsert_raw_pitch_events(db, import_run_id="r1", rows=list(rows.values()), batch_size=2)

        changed = dict(rows)
        changed["a"]["release_speed"] = 100.5
        changed["a"]["raw_payload_hash"] = "h-new"
        third = upsert_raw_pitch_events(db, import_run_id="r3", rows=list(changed.values()), batch_size=2)
        assert third.updated == 1
        assert third.unchanged == 6
        assert db.query(RawPitchEvent).count() == 7
        event = db.query(RawPitchEvent).filter_by(game_pk=716180, at_bat_number=0, pitch_number=1).one()
        assert event.release_speed == 100.5
        assert event.raw_payload_hash == "h-new"


class TestChunkingSeguro:
    """§3: subdivisión por umbral y alineación pipeline/adapter."""

    def test_subdivide_por_umbral(self, db):
        log = {}
        # Fixture de 7 filas devuelto siempre; umbral 4 → cada chunk cerca/bajo de 4 se parte.
        adapter = _adapter(threshold=4, chunk_days=30, log=log)
        records = adapter.fetch_date_range(dt.date(2026, 3, 1), dt.date(2026, 4, 30))
        assert log["requests"] > 1
        # Los nodos internos descartan su copia al dividir; las hojas aportan 7 c/u.
        assert len(records) >= 7
        assert len(records) % 7 == 0

    def test_no_subdivide_bajo_umbral(self, db):
        log = {}
        adapter = _adapter(threshold=25000, chunk_days=10, log=log)
        records = adapter.fetch_date_range(dt.date(2026, 4, 1), dt.date(2026, 4, 7))
        assert log["requests"] == 1
        assert len(records) == 7

    def test_alinea_chunk_days_pipeline_adapter(self, db):
        log = {}
        pipeline = StatcastRawPipeline(db, _adapter(chunk_days=10, log=log), chunk_days=10)
        result = pipeline.run(date_from=dt.date(2026, 4, 1), date_to=dt.date(2026, 4, 7))
        assert result.rows_extracted == 7
        assert result.rows_inserted == 7
        assert log["requests"] == 1


class TestEstadosYPropagacion:
    """§1/§5: FAILED propagado y PARTIAL semánticamente correcto."""

    def test_partial_cuando_hay_rechazos(self, db):
        bad = _csv_rows().replace("716180,2026-04-01,1,1,", "716180,2026-04-01,0,1,", 1)
        pipeline = StatcastRawPipeline(db, _adapter(bad), chunk_days=10)
        result = pipeline.run(date_from=dt.date(2026, 4, 1), date_to=dt.date(2026, 4, 7))
        assert result.rows_rejected > 0
        run = db.query(DataImportRun).one()
        assert run.status == ImportStatus.PARTIAL

    def test_falla_http_propaga_y_deja_failed(self, db):
        adapter = StatcastSourceAdapter(
            http=ExternalHttpClient(transport=httpx.MockTransport(lambda request: httpx.Response(500, request=request))),
            base_url="https://savant.test",
        )
        pipeline = StatcastRawPipeline(db, adapter, chunk_days=10)
        with pytest.raises(httpx.HTTPStatusError):
            pipeline.run(date_from=dt.date(2026, 4, 1), date_to=dt.date(2026, 4, 7))
        run = db.query(DataImportRun).one()
        assert run.status == ImportStatus.FAILED
        assert run.error_summary


class TestRunPlayer:
    """§7: lógica de import-statcast-player fuera de la CLI."""

    def test_run_player_ingiere_y_centraliza_version(self, db):
        pipeline = StatcastRawPipeline(db, _adapter(chunk_days=10), chunk_days=10)
        result = pipeline.run_player(
            mlb_id=660271, role="batter", date_from=dt.date(2026, 4, 1), date_to=dt.date(2026, 4, 7)
        )
        assert result.rows_inserted == 7
        run = db.query(DataImportRun).one()
        assert run.pipeline_version == ETL_PIPELINE_VERSION
        assert run.status == ImportStatus.SUCCESS

    def test_run_player_rechazo_queda_partial(self, db):
        bad = _csv_rows().replace("716180,2026-04-01,1,1,", "716180,2026-04-01,0,1,", 1)
        pipeline = StatcastRawPipeline(db, _adapter(bad, chunk_days=10), chunk_days=10)
        result = pipeline.run_player(
            mlb_id=660271, role="batter", date_from=dt.date(2026, 4, 1), date_to=dt.date(2026, 4, 7)
        )
        assert result.rows_rejected == 1
        run = db.query(DataImportRun).one()
        assert run.status == ImportStatus.PARTIAL


class TestResolucionDesdeRaw:
    """§6: run resuelve solo Players presentes en RAW (sin rosters)."""

    def test_resuelve_player_de_raw(self, db):
        from etl.pipelines.metadata import MetadataPipeline
        from etl.sources.mlb import MLBStatsApiClient

        # RAW con ids 660271 (batter) / 669373 (pitcher).
        _pipeline(db).run(date_from=dt.date(2026, 4, 1), date_to=dt.date(2026, 4, 7))
        assert db.query(Player).count() == 0

        def handler(request):
            prefix = "/people/"
            if request.url.path.startswith(prefix):
                pid = int(request.url.path[len(prefix):])
                return httpx.Response(
                    200,
                    json={"people": [
                        {"id": pid, "fullName": "Jugador", "firstName": "J", "lastName": "P",
                         "primaryPosition": {"abbreviation": "P"}}]},
                    request=request,
                )
            return httpx.Response(404, request=request)

        client = MLBStatsApiClient(
            http=ExternalHttpClient(transport=httpx.MockTransport(handler)), base_url="https://mlb.test"
        )
        result = MetadataPipeline(db, client).resolve_players_from_raw(
            season=2026, data_start_date=dt.date(2026, 4, 1), data_end_date=dt.date(2026, 4, 7)
        )
        assert result.players == 2
        assert result.unresolved == []
        assert db.query(Player).count() == 2

    def test_sin_raw_no_resuelve_nada(self, db):
        from etl.pipelines.metadata import MetadataPipeline
        from etl.sources.mlb import MLBStatsApiClient

        def handler(request):
            return httpx.Response(404, request=request)

        client = MLBStatsApiClient(
            http=ExternalHttpClient(transport=httpx.MockTransport(handler)), base_url="https://mlb.test"
        )
        result = MetadataPipeline(db, client).resolve_players_from_raw(
            season=2026, data_start_date=dt.date(2026, 4, 1), data_end_date=dt.date(2026, 4, 7)
        )
        assert result.players == 0
        assert db.query(Player).count() == 0


class TestCliRunSeDetiene:
    """§1/§2: si RAW falla, el run corta sin metadata ni analytics."""

    def test_run_detiene_cadena_si_raw_falla(self, monkeypatch):
        import etl.cli

        calls = {"analytics": 0, "metadata": 0}

        class FakeRaw:
            def __init__(self, db, adapter):
                pass

            def run(self, **kwargs):
                raise RuntimeError("raw explotó")

        class FakeMetadata:
            def __init__(self, db, client):
                pass

            def resolve_players_from_raw(self, **kwargs):
                calls["metadata"] += 1

        class FakeAnalytics:
            def __init__(self, db):
                pass

            def rebuild(self, **kwargs):
                calls["analytics"] += 1

        monkeypatch.setattr("etl.cli.StatcastRawPipeline", FakeRaw)
        monkeypatch.setattr("etl.cli.MetadataPipeline", FakeMetadata)
        monkeypatch.setattr("etl.cli.AnalyticsPipeline", FakeAnalytics)

        rc = etl.cli.main(["run", "--season", "2026", "--from", "2026-04-01", "--to", "2026-04-05"])
        assert rc == 1
        assert calls["metadata"] == 0
        assert calls["analytics"] == 0