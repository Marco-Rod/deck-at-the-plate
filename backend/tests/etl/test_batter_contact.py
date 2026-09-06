"""Pruebas de Contact para batter ratings-2.0."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import BatterSeasonStats, LeagueMetricDistribution, Player, PlayerSeason
from etl.services.batter_contact import calculate_batter_contact


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


def _batter(db, mlb_id=660271, *, swings=72, contact=0.638889, whiff=0.361111, ab=33, avg=0.15152):
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
        pitches_seen=max(swings, 1),
        swings=swings,
        whiffs=round(swings * whiff),
        contact_rate=contact,
        whiff_rate=whiff,
        avg=avg,
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


def _seed_distributions(db):
    _distribution(db, "contact_rate", 0.75)
    _distribution(db, "avg", 0.25)
    _distribution(db, "whiff_rate", 0.25)


def _calculate(db, mlb_id=660271):
    db.commit()
    return calculate_batter_contact(
        db,
        mlb_id=mlb_id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )


def test_contact_es_auditable_y_aplica_estabilizaciones(db):
    _batter(db)
    _seed_distributions(db)
    result = _calculate(db)
    components = {component.metric: component for component in result.components}

    assert result.rating is not None
    assert result.rating_model_version == "ratings-2.0"
    assert components["contact_rate"].stabilization == 50
    assert components["avg"].stabilization == 40
    assert components["whiff_rate"].stabilization == 50
    assert components["contact_rate"].shrinkage_weight == pytest.approx(72 / 122)
    assert components["avg"].shrinkage_weight == pytest.approx(33 / 73)
    assert components["whiff_rate"].percentile > 0.5


@pytest.mark.parametrize(
    ("field", "low", "high", "higher_is_better"),
    [
        ("contact_rate", 0.40, 0.80, True),
        ("avg", 0.10, 0.40, True),
        ("whiff_rate", 0.10, 0.40, False),
    ],
)
def test_monotonicidad_por_componente(db, field, low, high, higher_is_better):
    row = _batter(db)
    _seed_distributions(db)
    setattr(row, field, low)
    low_rating = _calculate(db).rating
    setattr(row, field, high)
    high_rating = _calculate(db).rating

    if higher_is_better:
        assert high_rating >= low_rating
    else:
        assert high_rating <= low_rating


def test_muestra_pequena_se_acerca_mas_al_baseline(db):
    _batter(db, 1, swings=5, contact=0.90, whiff=0.10, ab=5, avg=0.40)
    _batter(db, 2, swings=100, contact=0.90, whiff=0.10, ab=100, avg=0.40)
    _seed_distributions(db)
    small = {c.metric: c for c in _calculate(db, 1).components}
    large = {c.metric: c for c in _calculate(db, 2).components}

    for metric in ("contact_rate", "avg", "whiff_rate"):
        baseline = small[metric].league_baseline
        assert abs(small[metric].adjusted - baseline) < abs(large[metric].adjusted - baseline)


def test_falta_componente_no_produce_contact(db):
    _batter(db)
    _distribution(db, "contact_rate", 0.75)
    _distribution(db, "avg", 0.25)
    result = _calculate(db)
    assert result.rating is None
    assert result.skipped_metrics == ["whiff_rate"]
