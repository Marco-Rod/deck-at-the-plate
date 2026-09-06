"""Pruebas de componentes y cobertura de Control ratings-2.0."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import LeagueMetricDistribution, PitcherSeasonStats, Player, PlayerSeason
from etl.services.pitcher_control import calculate_control_candidate


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


def _seed_pitcher(db):
    player = Player(mlb_id=650911, full_name="Cristopher Sanchez", primary_position="SP")
    db.add(player)
    db.flush()
    ps = PlayerSeason(player_id=player.id, season=2026, data_start_date=START, data_end_date=END)
    db.add(ps)
    db.flush()
    row = PitcherSeasonStats(
        player_season_id=ps.id, pitches=91, batters_faced=25,
        zone_pitches=43, zone_opportunities=91, zone_rate=0.472527,
        first_pitch_strikes=19, first_pitch_opportunities=25, first_pitch_strike_rate=0.76,
        walks=1, walk_opportunities=25, walk_rate=0.04,
        hit_by_pitches=0, hbp_opportunities=25, hbp_rate=0,
        strikeouts=5, strikeout_opportunities=25,
        swings=42, whiffs=15, called_strikes=10, csw=25, csw_opportunities=91,
    )
    db.add(row)
    return row


def _distribution(db, metric, baseline=0.5, tied_zero=False):
    points = dict(minimum=0, p05=0.05, p10=0.10, p25=0.25, p50=0.50,
                  p75=0.75, p90=0.90, p95=0.95, maximum=1)
    if tied_zero:
        points.update(minimum=0, p05=0, p10=0, p25=0, p50=0, p75=0,
                      p90=0.03, p95=0.04, maximum=0.05)
    db.add(LeagueMetricDistribution(
        season=2026, role="PITCHER", metric=metric, pitch_type=None, pitch_family=None,
        population_size=20, sample_size_total=500, population_mean=baseline,
        league_baseline=baseline, median=points["p50"], stddev=0.1,
        distribution_version="dist-1.0", data_start_date=START, data_end_date=END,
        **points,
    ))


def test_control_aplica_shrinkage_y_direcciones(db):
    _seed_pitcher(db)
    for metric in ("walk_rate", "zone_rate", "first_pitch_strike_rate"):
        _distribution(db, metric)
    _distribution(db, "hbp_rate", baseline=0, tied_zero=True)
    db.commit()
    result = calculate_control_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    components = {component.metric: component for component in result.components}
    walk = components["walk_rate"]
    assert abs(walk.shrinkage_weight - 25 / 175) < 1e-12
    assert abs(walk.adjusted - (25 / 175 * 0.04 + 150 / 175 * 0.5)) < 1e-12
    assert walk.percentile > 0.5  # BB% menor invierte el percentil estadístico.
    assert components["zone_rate"].percentile < 0.5
    assert components["first_pitch_strike_rate"].percentile > 0.5
    assert components["hbp_rate"].rating < 99
    assert result.weight_coverage == 1
    assert result.rating is not None


def test_control_renormaliza_con_cobertura_exacta_75_por_ciento(db):
    _seed_pitcher(db)
    _distribution(db, "walk_rate")
    _distribution(db, "zone_rate")
    db.commit()
    result = calculate_control_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    assert result.weight_coverage == 0.75
    assert result.rating == round(sum(component.contribution for component in result.components))
    assert set(result.skipped_metrics) == {"first_pitch_strike_rate", "hbp_rate"}


def test_control_rechaza_cobertura_menor_a_75_por_ciento(db):
    _seed_pitcher(db)
    _distribution(db, "walk_rate")
    db.commit()
    result = calculate_control_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    assert result.weight_coverage == 0.45
    assert result.rating is None
    assert all(component.contribution == 0 for component in result.components)
