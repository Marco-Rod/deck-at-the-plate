"""Pruebas de Power para batter ratings-2.0."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import BatterSeasonStats, LeagueMetricDistribution, Player, PlayerSeason
from etl.services.batter_power import calculate_batter_power
from etl.services.rating_math import round_rating


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


def _batter(
    db,
    mlb_id=660271,
    *,
    ab=33,
    avg=0.15152,
    slg=0.24242,
    barrel_opportunities=20,
    barrel_rate=0.05,
    hard_hit_opportunities=20,
    hard_hit_rate=0.35,
):
    player = Player(mlb_id=mlb_id, full_name=f"Batter {mlb_id}", primary_position="TWP")
    db.add(player)
    db.flush()
    snapshot = PlayerSeason(
        player_id=player.id, season=2026, data_start_date=START, data_end_date=END
    )
    db.add(snapshot)
    db.flush()
    row = BatterSeasonStats(
        player_season_id=snapshot.id,
        pa=max(ab, 1),
        ab=ab,
        hits=0,
        balls_in_play=max(barrel_opportunities, hard_hit_opportunities),
        barrels=round(barrel_opportunities * barrel_rate),
        barrel_opportunities=barrel_opportunities,
        hard_hits=round(hard_hit_opportunities * hard_hit_rate),
        hard_hit_opportunities=hard_hit_opportunities,
        avg=avg,
        slg=slg,
        barrel_rate=barrel_rate,
        hard_hit_rate=hard_hit_rate,
    )
    db.add(row)
    return row


def _distribution(db, metric, baseline):
    db.add(LeagueMetricDistribution(
        season=2026,
        role="BATTER",
        metric=metric,
        pitch_type=None,
        pitch_family=None,
        population_size=30,
        sample_size_total=900,
        population_mean=baseline,
        league_baseline=baseline,
        median=0.5,
        stddev=0.1,
        minimum=0,
        p05=0.05,
        p10=0.10,
        p25=0.25,
        p50=0.50,
        p75=0.75,
        p90=0.90,
        p95=0.95,
        maximum=1,
        distribution_version="dist-1.0",
        data_start_date=START,
        data_end_date=END,
    ))


def _seed_distributions(db, baselines=None):
    baselines = baselines or {
        "iso": 0.15,
        "barrel_rate": 0.08,
        "hard_hit_rate": 0.38,
        "slg": 0.40,
    }
    for metric, baseline in baselines.items():
        _distribution(db, metric, baseline)


def _calculate(db, mlb_id=660271):
    db.commit()
    return calculate_batter_power(
        db,
        mlb_id=mlb_id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )


def test_power_usa_formula_denominadores_y_estabilizaciones(db):
    row = _batter(db)
    _seed_distributions(db)
    result = _calculate(db)
    components = {component.metric: component for component in result.components}

    assert result.rating is not None
    assert components["iso"].observed == pytest.approx(float(row.slg - row.avg))
    assert (components["iso"].sample_size, components["iso"].stabilization) == (33, 40)
    assert (components["slg"].sample_size, components["slg"].stabilization) == (33, 40)
    assert (
        components["barrel_rate"].sample_size,
        components["barrel_rate"].stabilization,
    ) == (20, 30)
    assert (
        components["hard_hit_rate"].sample_size,
        components["hard_hit_rate"].stabilization,
    ) == (20, 30)
    assert result.rating == round_rating(sum(c.contribution for c in result.components))


def test_power_es_monotonico_para_iso_derivado(db):
    row = _batter(db)
    _seed_distributions(db)
    # Con SLG fijo, bajar AVG aumenta ISO sin modificar otro componente de Power.
    row.avg = 0.35
    low_iso_rating = _calculate(db).rating
    row.avg = 0.05
    high_iso_rating = _calculate(db).rating
    assert high_iso_rating >= low_iso_rating


@pytest.mark.parametrize("field", ["barrel_rate", "hard_hit_rate", "slg"])
def test_power_es_monotonico_para_cada_metrica(db, field):
    row = _batter(db)
    _seed_distributions(db)
    setattr(row, field, 0.10)
    low = _calculate(db).rating
    setattr(row, field, 0.60)
    high = _calculate(db).rating
    assert high >= low


def test_muestra_pequena_se_acerca_mas_al_baseline(db):
    _batter(db, 1, ab=5, avg=0.10, slg=0.60, barrel_opportunities=5,
            barrel_rate=0.30, hard_hit_opportunities=5, hard_hit_rate=0.60)
    _batter(db, 2, ab=100, avg=0.10, slg=0.60, barrel_opportunities=100,
            barrel_rate=0.30, hard_hit_opportunities=100, hard_hit_rate=0.60)
    _seed_distributions(db)
    small = {c.metric: c for c in _calculate(db, 1).components}
    large = {c.metric: c for c in _calculate(db, 2).components}
    for metric in ("iso", "barrel_rate", "hard_hit_rate", "slg"):
        baseline = small[metric].league_baseline
        assert abs(small[metric].adjusted - baseline) < abs(large[metric].adjusted - baseline)


def test_composite_punto_cinco_redondea_hacia_arriba(db):
    slg_for_rating_75 = 35 / 59
    _batter(db, avg=slg_for_rating_75 - 0.5, slg=slg_for_rating_75,
            barrel_rate=0.5, hard_hit_rate=0.5)
    _seed_distributions(db, {
        "iso": 0.5,
        "barrel_rate": 0.5,
        "hard_hit_rate": 0.5,
        "slg": slg_for_rating_75,
    })
    result = _calculate(db)
    assert [component.rating for component in result.components] == [70, 70, 70, 75]
    assert sum(component.contribution for component in result.components) == pytest.approx(70.5)
    assert result.rating == 71


def test_falta_componente_no_produce_power(db):
    _batter(db)
    for metric, baseline in (("iso", 0.15), ("barrel_rate", 0.08), ("slg", 0.40)):
        _distribution(db, metric, baseline)
    result = _calculate(db)
    assert result.rating is None
    assert result.skipped_metrics == ["hard_hit_rate"]
