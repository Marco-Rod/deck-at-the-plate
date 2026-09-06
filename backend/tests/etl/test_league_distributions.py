"""Pruebas del constructor versionado de distribuciones de liga."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import LeagueMetricDistribution, PitcherSeasonStats, Player, PlayerSeason
from etl.services.league_distributions import build_league_distributions
from etl.services.percentiles import percentile, percentile_rank


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _pitcher(db, mlb_id: int, pitches: int, batters: int, factor: float):
    player = Player(mlb_id=mlb_id, full_name=f"Pitcher {mlb_id}")
    db.add(player)
    db.flush()
    season = PlayerSeason(
        player_id=player.id, season=2026, data_start_date=START, data_end_date=END,
        batters_faced=batters,
    )
    db.add(season)
    db.flush()
    zone = round(0.40 + factor * 0.10, 6)
    fps = round(0.50 + factor * 0.10, 6)
    walk = round(0.12 - factor * 0.04, 6)
    strikeout = round(0.18 + factor * 0.10, 6)
    hbp = round(0.04 - factor * 0.02, 6)
    csw_rate = round(0.22 + factor * 0.10, 6)
    csw = round(pitches * csw_rate)
    called = csw // 2
    row = PitcherSeasonStats(
        player_season_id=season.id, pitches=pitches, batters_faced=batters,
        zone_pitches=round(pitches * zone), zone_opportunities=pitches, zone_rate=zone,
        first_pitch_strikes=round(batters * fps), first_pitch_opportunities=batters,
        first_pitch_strike_rate=fps,
        walks=round(batters * walk), walk_opportunities=batters, walk_rate=walk,
        strikeouts=round(batters * strikeout), strikeout_opportunities=batters, strikeout_rate=strikeout,
        hit_by_pitches=round(batters * hbp), hbp_opportunities=batters, hbp_rate=hbp,
        called_strikes=called, whiffs=csw - called, csw=csw,
        csw_opportunities=pitches, csw_rate=csw_rate,
    )
    db.add(row)
    return row


def test_percentiles_interpolan_e_invierten_direccion():
    assert percentile([0, 10, 20, 30], 0.25) == 7.5
    assert percentile([0, 10, 20, 30], 0.50) == 15
    points = [(0, 0), (10, 0.5), (20, 1)]
    assert percentile_rank(15, points) == 0.75
    assert percentile_rank(15, points, direction="lower") == 0.25


def test_builder_filtra_muestra_y_es_idempotente(db):
    rows = [_pitcher(db, 1, 100, 20, 0.0), _pitcher(db, 2, 200, 40, 0.5), _pitcher(db, 3, 300, 60, 1.0)]
    _pitcher(db, 4, 10, 2, 1.0)  # Excluido de las seis distribuciones.
    db.commit()

    first = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END,
    )
    assert (first.created, first.updated, first.unchanged, first.skipped) == (6, 0, 0, 0)
    zone = db.query(LeagueMetricDistribution).filter_by(metric="zone_rate").one()
    assert zone.population_size == 3
    assert zone.sample_size_total == 600
    assert float(zone.p50) == 0.45
    assert float(zone.population_mean) == 0.45
    assert abs(float(zone.league_baseline) - 0.46666667) < 1e-8
    assert zone.distribution_version == "dist-1.0"

    second = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END,
    )
    assert (second.created, second.updated, second.unchanged) == (0, 0, 6)

    rows[0].zone_rate = 0.43
    db.commit()
    changed = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END,
    )
    assert (changed.created, changed.updated, changed.unchanged) == (0, 1, 5)


def test_version_nueva_no_sobrescribe_historial(db):
    _pitcher(db, 1, 100, 20, 0.5)
    db.commit()
    build_league_distributions(db, season=2026, role="pitcher", data_start_date=START, data_end_date=END)
    result = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END,
        distribution_version="mlb-2026-v2",
    )
    assert result.created == 6
    assert db.query(LeagueMetricDistribution).count() == 12


def test_baseline_pondera_oportunidades_sin_alterar_distribucion(db):
    _pitcher(db, 1, 50, 20, 1.0)   # zone_rate=.50
    _pitcher(db, 2, 950, 40, 0.0)  # zone_rate=.40
    db.commit()
    build_league_distributions(db, season=2026, role="pitcher", data_start_date=START, data_end_date=END)
    zone = db.query(LeagueMetricDistribution).filter_by(metric="zone_rate").one()
    assert float(zone.population_mean) == 0.45
    assert float(zone.league_baseline) == 0.405
    assert float(zone.p50) == 0.45
