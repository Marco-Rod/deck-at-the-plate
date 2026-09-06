"""Pruebas de Vision para batter ratings-2.0."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import BatterSeasonStats, LeagueMetricDistribution, Player, PlayerSeason
from etl.services.batter_vision import calculate_batter_vision
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
    chase_opportunities=86,
    chase_rate=0.302326,
    swings=72,
    whiff_rate=0.361111,
    pa=38,
    walk_rate=3 / 38,
    strikeout_rate=13 / 38,
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
        pa=pa,
        ab=max(pa - 5, 0),
        pitches_seen=max(chase_opportunities, swings),
        swings=swings,
        whiffs=round(swings * whiff_rate),
        chase_opportunities=chase_opportunities,
        chases=round(chase_opportunities * chase_rate),
        chase_rate=chase_rate,
        whiff_rate=whiff_rate,
        walks=round(pa * walk_rate),
        strikeouts=round(pa * strikeout_rate),
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
        population_size=35,
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


def _seed_distributions(db):
    for metric, baseline in (
        ("chase_rate", 0.28),
        ("whiff_rate", 0.25),
        ("walk_rate", 0.09),
        ("strikeout_rate", 0.23),
    ):
        _distribution(db, metric, baseline)


def _calculate(db, mlb_id=660271):
    db.commit()
    return calculate_batter_vision(
        db,
        mlb_id=mlb_id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )


def test_vision_usa_formula_denominadores_y_estabilizaciones(db):
    _batter(db)
    _seed_distributions(db)
    result = _calculate(db)
    components = {component.metric: component for component in result.components}

    assert result.rating is not None
    assert result.rating_model_version == "ratings-2.0"
    assert (components["chase_rate"].sample_size, components["chase_rate"].stabilization) == (86, 50)
    assert (components["whiff_rate"].sample_size, components["whiff_rate"].stabilization) == (72, 50)
    assert (components["walk_rate"].sample_size, components["walk_rate"].stabilization) == (38, 40)
    assert (components["strikeout_rate"].sample_size, components["strikeout_rate"].stabilization) == (38, 40)
    assert components["walk_rate"].observed == pytest.approx(3 / 38)
    assert components["strikeout_rate"].observed == pytest.approx(13 / 38)
    assert {component.metric: component.component_weight for component in result.components} == {
        "chase_rate": 0.40,
        "whiff_rate": 0.30,
        "walk_rate": 0.20,
        "strikeout_rate": 0.10,
    }
    assert result.rating == round_rating(sum(c.contribution for c in result.components))


@pytest.mark.parametrize(
    ("field", "better", "worse"),
    [
        ("chase_rate", 0.10, 0.50),
        ("whiff_rate", 0.10, 0.50),
        ("walks", 8, 1),
        ("strikeouts", 2, 15),
    ],
)
def test_vision_es_monotonico_por_componente(db, field, better, worse):
    row = _batter(db)
    _seed_distributions(db)
    setattr(row, field, worse)
    worse_rating = _calculate(db).rating
    setattr(row, field, better)
    better_rating = _calculate(db).rating
    assert better_rating >= worse_rating


def test_muestra_pequena_se_acerca_mas_al_baseline(db):
    _batter(db, 1, chase_opportunities=5, chase_rate=0.50, swings=5,
            whiff_rate=0.50, pa=5, walk_rate=0.20, strikeout_rate=0.40)
    _batter(db, 2, chase_opportunities=100, chase_rate=0.50, swings=100,
            whiff_rate=0.50, pa=100, walk_rate=0.20, strikeout_rate=0.40)
    _seed_distributions(db)
    small = {c.metric: c for c in _calculate(db, 1).components}
    large = {c.metric: c for c in _calculate(db, 2).components}
    for metric in ("chase_rate", "whiff_rate", "walk_rate", "strikeout_rate"):
        baseline = small[metric].league_baseline
        assert abs(small[metric].adjusted - baseline) < abs(large[metric].adjusted - baseline)


def test_falta_componente_no_produce_vision(db):
    _batter(db)
    for metric, baseline in (
        ("chase_rate", 0.28),
        ("whiff_rate", 0.25),
        ("walk_rate", 0.09),
    ):
        _distribution(db, metric, baseline)
    result = _calculate(db)
    assert result.rating is None
    assert result.skipped_metrics == ["strikeout_rate"]
