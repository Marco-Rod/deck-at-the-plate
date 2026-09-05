"""Pruebas de agregadores y pipeline analytics (spec §25-§32, §40)."""

import datetime as dt
import pathlib

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    BatterHandednessSplit,
    BatterPitchFamilyProfile,
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
    RawPitchEvent,
)
from app.core.enums import ImportStatus
from etl.http.client import ExternalHttpClient
from etl.pipelines.statcast import StatcastRawPipeline
from etl.sources.statcast import StatcastSourceAdapter
from etl.loaders.core import upsert_player, upsert_player_season, upsert_team
from etl.dto import PlayerSourceRecord, TeamSourceRecord
from etl.pipelines.analytics import AnalyticsPipeline

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

W_FROM = dt.date(2026, 4, 1)
W_TO = dt.date(2026, 4, 7)
SEASON = 2026


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _seed(db):
    """Carga raw con el fixture y crea players + player_season del snapshot."""
    def handler(request):
        return httpx.Response(200, text=(FIXTURES / "statcast_small.csv").read_text(), request=request)

    adapter = StatcastSourceAdapter(
        http=ExternalHttpClient(transport=httpx.MockTransport(handler)),
        base_url="https://savant.test",
    )
    StatcastRawPipeline(db, adapter, chunk_days=10).run(date_from=W_FROM, date_to=W_TO)

    upsert_team(db, TeamSourceRecord(mlb_team_id=119, name="Dodgers", abbreviation="LAD", location_name="Los Angeles", active=True))
    upd_team = upsert_team(db, TeamSourceRecord(mlb_team_id=143, name="Phillies", abbreviation="PHI", location_name="Philadelphia", active=True))
    ohtani = upsert_player(db, PlayerSourceRecord(mlb_id=660271, full_name="Shohei Ohtani", bats="L", throws="L"))
    pit = upsert_player(db, PlayerSourceRecord(mlb_id=669373, full_name="Fake Pitcher", bats="R", throws="L"))
    for player in (ohtani, pit):
        upsert_player_season(db, player=player, season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    db.commit()
    return ohtani, pit


def test_analytics_builds_y_no_duplica(db):
    ohtani, pit = _seed(db)
    pipeline = AnalyticsPipeline(db)
    first = pipeline.rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    assert first.profiles_created > 0
    assert first.players_processed == 2
    assert first.analytics_rejected == 0

    second = pipeline.rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    assert first.profiles_created == second.profiles_created

    b_pitcher = db.query(PitcherSeasonStats).count()
    b_batter = db.query(BatterSeasonStats).count()
    assert db.query(BatterSeasonStats).count() == 1
    assert db.query(PitcherSeasonStats).count() == 1


def test_batter_baseline_from_fixture(db):
    _seed(db)
    AnalyticsPipeline(db).rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    row = db.query(BatterSeasonStats).one()
    assert row.pa == 2
    assert row.hits == 2
    assert row.singles == 1
    assert row.home_runs == 1
    assert row.ab == 2
    assert float(row.avg) == 1.0
    assert float(row.slg) == 2.5
    assert row.pitches_seen == 7
    assert row.swings == 4
    assert row.whiffs == 2
    assert float(row.whiff_rate) == 0.5


def test_pitcher_baseline_from_fixture(db):
    _seed(db)
    AnalyticsPipeline(db).rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    row = db.query(PitcherSeasonStats).one()
    assert row.batters_faced == 2
    assert row.pitches == 7
    assert row.hits_allowed == 2
    assert row.home_runs_allowed == 1
    assert row.strikeouts == 0
    assert float(row.whiff_rate) == 0.5


def test_zona_familia_y_handedness_creados(db):
    _seed(db)
    AnalyticsPipeline(db).rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    assert db.query(BatterZoneProfile).count() > 0
    assert db.query(PitcherZoneProfile).count() > 0
    assert db.query(BatterPitchFamilyProfile).count() > 0
    assert db.query(PitcherPitchProfile).count() > 0
    assert db.query(BatterHandednessSplit).count() >= 1
    assert db.query(PitcherHandednessSplit).count() >= 1
    assert db.query(BatterPitcherMatchup).count() == 1


def test_zone_profile_denominadores(db):
    _seed(db)
    AnalyticsPipeline(db).rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    for row in db.query(BatterZoneProfile).all():
        assert row.sample_size == row.pitches_seen
        assert row.zone >= 1 and row.zone <= 9
    for row in db.query(PitcherZoneProfile).all():
        assert row.sample_size == row.pitches


def test_arsenal_usage_y_velocidad(db):
    _seed(db)
    AnalyticsPipeline(db).rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    rows = db.query(PitcherPitchProfile).all()
    by_type = {r.pitch_type: r for r in rows if r.batter_side == "ALL"}
    ff = by_type["FF"]
    assert ff.pitch_count == 4
    assert ff.pitch_family == "FASTBALL"
    assert abs(float(ff.usage_rate) - 4 / 7) < 1e-6
    assert float(ff.avg_velocity) > 97
    assert ff.sample_size == ff.pitch_count
    assert by_type["SL"].pitch_family == "BREAKING"
    assert by_type["CH"].pitch_family == "OFFSPEED"


def test_run_success_y_analytics_rechazos_cero(db):
    _seed(db)
    result = AnalyticsPipeline(db).rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    run = db.query(DataImportRun).filter_by(source="ANALYTICS").one()
    assert run.status == ImportStatus.SUCCESS
    assert result.import_run_id == run.id


def test_sin_player_season_no_crashea(db):
    db.commit()
    result = AnalyticsPipeline(db).rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    assert result.players_processed == 0