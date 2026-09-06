"""Pruebas de shrinkage y percentil de Velocity ratings-2.0."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import LeagueMetricDistribution, PitcherSeasonStats, Player, PlayerSeason
from etl.services.pitcher_velocity import calculate_velocity_candidate


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


def _seed(db, avg_velocity=90.27, pitches=91):
    player = Player(mlb_id=650911, full_name="Cristopher Sanchez", primary_position="SP")
    db.add(player)
    db.flush()
    ps = PlayerSeason(player_id=player.id, season=2026, data_start_date=START, data_end_date=END)
    db.add(ps)
    db.flush()
    db.add(PitcherSeasonStats(
        player_season_id=ps.id, pitches=pitches, avg_velocity=avg_velocity,
        csw_opportunities=pitches,
    ))


def _distribution(db):
    db.add(LeagueMetricDistribution(
        season=2026, role="PITCHER", metric="avg_velocity",
        pitch_type=None, pitch_family=None, population_size=20, sample_size_total=2000,
        population_mean=90, league_baseline=88.77960138, median=89.5, stddev=2,
        minimum=84, p05=85, p10=86, p25=88, p50=89.5, p75=91,
        p90=93, p95=94, maximum=96, distribution_version="dist-1.0",
        data_start_date=START, data_end_date=END,
    ))


def test_velocity_aplica_shrinkage_antes_del_percentil(db):
    _seed(db)
    _distribution(db)
    db.commit()
    result = calculate_velocity_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    expected_weight = 91 / 291
    expected_adjusted = expected_weight * 90.27 + (1 - expected_weight) * 88.77960138
    assert abs(result.shrinkage_weight - expected_weight) < 1e-12
    assert abs(result.adjusted - expected_adjusted) < 1e-12
    assert result.sample_size == 91
    assert result.stabilization == 200
    assert result.percentile is not None
    assert result.rating is not None
    assert result.rating_model_version == "ratings-2.0"


def test_velocity_higher_is_better(db):
    _seed(db, avg_velocity=94)
    _distribution(db)
    db.commit()
    high = calculate_velocity_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    pitcher = db.query(PitcherSeasonStats).one()
    pitcher.avg_velocity = 86
    db.commit()
    low = calculate_velocity_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    assert high.percentile > low.percentile
    assert high.rating > low.rating


def test_velocity_sin_distribucion_no_inventa_rating(db):
    _seed(db)
    db.commit()
    result = calculate_velocity_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    assert result.rating is None
    assert result.unavailable_reason == "distribución avg_velocity ausente"
