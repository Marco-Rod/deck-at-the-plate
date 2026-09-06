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
from etl.aggregators.metrics import PitcherCounter

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
    assert row.swings == 4
    assert row.whiffs <= row.swings
    assert float(row.whiff_rate) == 0.5
    assert row.zone_pitches == 6
    assert row.zone_opportunities == 6
    assert float(row.zone_rate) == 1.0
    assert row.first_pitch_strikes == 1
    assert row.first_pitch_opportunities == 2
    assert float(row.first_pitch_strike_rate) == 0.5
    assert row.hit_by_pitches == 0
    assert row.hbp_opportunities == 2
    assert float(row.hbp_rate) == 0.0
    assert row.walk_opportunities == 2
    assert float(row.walk_rate) == 0.0
    assert row.strikeout_opportunities == 2
    assert float(row.strikeout_rate) == 0.0
    assert row.called_strikes == 1
    assert row.whiffs == 2
    assert row.csw == 3
    assert row.csw_opportunities == 7
    assert abs(float(row.csw_rate) - 3 / 7) < 1e-6


def test_pitcher_rates_conservan_numerador_denominador_y_rate():
    def pitch(at_bat, number, description, event, statcast_zone, game_zone):
        return RawPitchEvent(
            game_pk=1,
            game_date=W_FROM,
            season=SEASON,
            at_bat_number=at_bat,
            pitch_number=number,
            batter_mlb_id=100 + at_bat,
            pitcher_mlb_id=669373,
            description=description,
            event=event,
            statcast_zone=statcast_zone,
            game_zone=game_zone,
        )

    counter = PitcherCounter(
        [
            pitch(1, 1, "called_strike", None, 1, 1),
            pitch(1, 2, "swinging_strike", "strikeout", 5, 5),
            pitch(2, 1, "ball", None, 11, None),
            pitch(2, 2, "ball", "walk", 12, None),
            pitch(3, 1, "hit_by_pitch", "hit_by_pitch", None, None),
        ]
    )

    assert (counter.zone_pitches, counter.zone_opportunities, counter.zone_rate) == (2, 4, 0.5)
    assert (
        counter.first_pitch_strikes,
        counter.first_pitch_opportunities,
        counter.first_pitch_strike_rate,
    ) == (1, 3, 0.333333)
    assert (counter.hit_by_pitches, counter.hbp_opportunities, counter.hbp_rate) == (1, 3, 0.333333)
    assert (counter.walks, counter.walk_opportunities, counter.walk_rate) == (1, 3, 0.333333)
    assert (
        counter.strikeouts,
        counter.strikeout_opportunities,
        counter.strikeout_rate,
    ) == (1, 3, 0.333333)
    assert (counter.csw, counter.csw_opportunities, counter.csw_rate) == (2, 5, 0.4)
    assert counter.swings == 1
    assert counter.whiffs <= counter.swings
    assert counter.whiff_rate == 1.0


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


def test_arsenal_persiste_pfx_source_por_pitch_type_y_handedness(db):
    _seed(db)
    pipeline = AnalyticsPipeline(db)
    pipeline.rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    rows = db.query(PitcherPitchProfile).filter_by(pitch_type="FF").all()
    by_side = {str(row.batter_side.value if hasattr(row.batter_side, "value") else row.batter_side): row for row in rows}

    assert set(by_side) == {"ALL", "L"}
    assert float(by_side["ALL"].avg_pfx_x) == 1.075
    assert float(by_side["ALL"].avg_pfx_z) == 5.05
    assert by_side["ALL"].avg_pfx_x == by_side["L"].avg_pfx_x
    assert by_side["ALL"].avg_pfx_z == by_side["L"].avg_pfx_z

    snapshot = {
        (row.pitch_type, str(row.batter_side)): (row.pitch_count, row.avg_pfx_x, row.avg_pfx_z)
        for row in db.query(PitcherPitchProfile).all()
    }
    pipeline.rebuild(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
    rebuilt = {
        (row.pitch_type, str(row.batter_side)): (row.pitch_count, row.avg_pfx_x, row.avg_pfx_z)
        for row in db.query(PitcherPitchProfile).all()
    }
    assert rebuilt == snapshot


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
