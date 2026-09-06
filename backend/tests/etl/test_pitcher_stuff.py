"""Pruebas de shrinkage, composición y cobertura de Stuff ratings-2.0."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import LeagueMetricDistribution, PitcherSeasonStats, Player, PlayerSeason
from etl.services.pitcher_stuff import calculate_stuff_candidate


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
    db.add(PitcherSeasonStats(
        player_season_id=ps.id, pitches=91, batters_faced=25,
        swings=48, whiffs=15, whiff_rate=0.3125,
        called_strikes=17, csw=32, csw_opportunities=91, csw_rate=0.351648,
        strikeouts=8, strikeout_opportunities=25, strikeout_rate=0.32,
        hbp_opportunities=25, walk_opportunities=25,
    ))


def _distribution(db, metric, baseline):
    db.add(LeagueMetricDistribution(
        season=2026, role="PITCHER", metric=metric, pitch_type=None, pitch_family=None,
        population_size=20, sample_size_total=1000, population_mean=0.3,
        league_baseline=baseline, median=0.3, stddev=0.1,
        minimum=0, p05=0.05, p10=0.10, p25=0.20, p50=0.30,
        p75=0.40, p90=0.50, p95=0.55, maximum=0.60,
        distribution_version="dist-1.0", data_start_date=START, data_end_date=END,
    ))


def test_stuff_aplica_shrinkage_y_compone_tres_metricas_higher(db):
    _seed_pitcher(db)
    for metric, baseline in (("whiff_rate", 0.25), ("csw_rate", 0.28), ("strikeout_rate", 0.22)):
        _distribution(db, metric, baseline)
    db.commit()
    result = calculate_stuff_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    components = {component.metric: component for component in result.components}
    assert components["whiff_rate"].sample_size == 48
    assert components["whiff_rate"].stabilization == 100
    assert abs(components["whiff_rate"].shrinkage_weight - 48 / 148) < 1e-12
    assert components["csw_rate"].sample_size == 91
    assert components["csw_rate"].stabilization == 200
    assert components["strikeout_rate"].sample_size == 25
    assert components["strikeout_rate"].stabilization == 150
    assert all(component.percentile > 0 for component in result.components)
    assert result.weight_coverage == 1
    assert result.rating == round(sum(component.contribution for component in result.components))


def test_stuff_renormaliza_si_falta_k_con_80_por_ciento(db):
    _seed_pitcher(db)
    _distribution(db, "whiff_rate", 0.25)
    _distribution(db, "csw_rate", 0.28)
    db.commit()
    result = calculate_stuff_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    assert result.weight_coverage == 0.8
    assert result.rating is not None
    assert result.skipped_metrics == ["strikeout_rate"]


def test_stuff_rechaza_whiff_mas_k_por_cobertura_70_por_ciento(db):
    _seed_pitcher(db)
    _distribution(db, "whiff_rate", 0.25)
    _distribution(db, "strikeout_rate", 0.22)
    db.commit()
    result = calculate_stuff_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    assert result.weight_coverage == 0.7
    assert result.rating is None
    assert result.skipped_metrics == ["csw_rate"]
