"""Pruebas del constructor versionado de distribuciones de liga."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.core.enums import PitchFamily, SplitHand
from app.models import (
    BatterSeasonStats,
    LeagueMetricDistribution,
    PitcherPitchProfile,
    PitcherSeasonStats,
    Player,
    PlayerSeason,
)
from etl.config.league_distributions import BATTER_METRICS
from etl.services.league_distributions import build_league_distributions
from etl.services.percentiles import (
    distribution_percentile_rank,
    percentile,
    percentile_rank,
    percentile_rating,
)


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
    whiffs = csw - called
    swings = max(whiffs, round(pitches * 0.5))
    row = PitcherSeasonStats(
        player_season_id=season.id, pitches=pitches, batters_faced=batters,
        zone_pitches=round(pitches * zone), zone_opportunities=pitches, zone_rate=zone,
        first_pitch_strikes=round(batters * fps), first_pitch_opportunities=batters,
        first_pitch_strike_rate=fps,
        walks=round(batters * walk), walk_opportunities=batters, walk_rate=walk,
        strikeouts=round(batters * strikeout), strikeout_opportunities=batters, strikeout_rate=strikeout,
        hit_by_pitches=round(batters * hbp), hbp_opportunities=batters, hbp_rate=hbp,
        called_strikes=called, swings=swings, whiffs=whiffs, csw=csw,
        csw_opportunities=pitches, csw_rate=csw_rate,
        avg_velocity=round(90 + factor * 5, 2),
        whiff_rate=round(whiffs / swings, 6),
    )
    db.add(row)
    return row


def _movement_profile(db, mlb_id: int, pitch_type: str, family, count: int, x: float, z: float):
    stats = _pitcher(db, mlb_id, max(count, 50), 20, 0.5)
    profile = PitcherPitchProfile(
        player_season_id=stats.player_season_id,
        pitch_type=pitch_type,
        pitch_family=family,
        batter_side=SplitHand.ALL,
        pitch_count=count,
        sample_size=count,
        usage_rate=1,
        avg_pfx_x=x,
        avg_pfx_z=z,
    )
    db.add(profile)
    return profile


def _batter(db, mlb_id: int, factor: float):
    player = Player(mlb_id=mlb_id, full_name=f"Batter {mlb_id}")
    db.add(player)
    db.flush()
    season = PlayerSeason(
        player_id=player.id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )
    db.add(season)
    db.flush()
    swings = 50 + int(factor * 10)
    whiffs = 10 + int(factor * 5)
    pa = 40 + int(factor * 10)
    ab = pa - 5
    balls_in_play = 20 + int(factor * 5)
    hard_opportunities = balls_in_play - 2
    barrel_opportunities = balls_in_play - 4
    row = BatterSeasonStats(
        player_season_id=season.id,
        pa=pa,
        ab=ab,
        hits=12,
        walks=5,
        strikeouts=10,
        pitches_seen=100,
        swings=swings,
        whiffs=whiffs,
        balls_in_play=balls_in_play,
        chases=10,
        chase_opportunities=40,
        hard_hits=8,
        hard_hit_opportunities=hard_opportunities,
        barrels=2,
        barrel_opportunities=barrel_opportunities,
        avg=0.250 + factor * 0.050,
        slg=0.400 + factor * 0.100,
        contact_rate=round((swings - whiffs) / swings, 6),
        whiff_rate=round(whiffs / swings, 6),
        chase_rate=0.25,
        hard_hit_rate=round(8 / hard_opportunities, 6),
        barrel_rate=round(2 / barrel_opportunities, 6),
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
    assert (first.created, first.updated, first.unchanged, first.skipped) == (8, 0, 0, 0)
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
    assert (second.created, second.updated, second.unchanged) == (0, 0, 8)

    rows[0].zone_rate = 0.43
    db.commit()
    changed = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END,
    )
    assert (changed.created, changed.updated, changed.unchanged) == (0, 1, 7)


def test_builder_batter_crea_diez_metricas_derivadas_y_es_idempotente(db):
    first_batter = _batter(db, 101, 0.0)
    second_batter = _batter(db, 102, 1.0)
    db.commit()

    first = build_league_distributions(
        db,
        season=2026,
        role="batter",
        data_start_date=START,
        data_end_date=END,
    )

    assert (first.created, first.updated, first.unchanged, first.skipped) == (10, 0, 0, 0)
    assert set(BATTER_METRICS) == {
        row.metric for row in db.query(LeagueMetricDistribution).filter_by(role="BATTER")
    }
    iso = db.query(LeagueMetricDistribution).filter_by(role="BATTER", metric="iso").one()
    walks = db.query(LeagueMetricDistribution).filter_by(
        role="BATTER", metric="walk_rate"
    ).one()
    strikeouts = db.query(LeagueMetricDistribution).filter_by(
        role="BATTER", metric="strikeout_rate"
    ).one()
    assert float(iso.minimum) == pytest.approx(float(first_batter.slg - first_batter.avg))
    assert float(iso.maximum) == pytest.approx(float(second_batter.slg - second_batter.avg))
    assert float(walks.maximum) == pytest.approx(first_batter.walks / first_batter.pa)
    assert float(strikeouts.maximum) == pytest.approx(
        first_batter.strikeouts / first_batter.pa
    )

    second = build_league_distributions(
        db,
        season=2026,
        role="batter",
        data_start_date=START,
        data_end_date=END,
    )
    assert (second.created, second.updated, second.unchanged) == (0, 0, 10)


def test_builder_batter_usa_denominador_real_como_sample(db):
    row = _batter(db, 101, 0.0)
    db.commit()
    build_league_distributions(
        db,
        season=2026,
        role="batter",
        data_start_date=START,
        data_end_date=END,
    )

    expected_samples = {
        metric: getattr(row, config.sample_field)
        for metric, config in BATTER_METRICS.items()
    }
    actual = {
        distribution.metric: distribution.sample_size_total
        for distribution in db.query(LeagueMetricDistribution).filter_by(role="BATTER")
    }
    assert actual == expected_samples
    assert {metric: config.direction for metric, config in BATTER_METRICS.items()} == {
        "contact_rate": "higher",
        "avg": "higher",
        "whiff_rate": "lower",
        "iso": "higher",
        "barrel_rate": "higher",
        "hard_hit_rate": "higher",
        "slg": "higher",
        "chase_rate": "lower",
        "walk_rate": "higher",
        "strikeout_rate": "lower",
    }


def test_version_nueva_no_sobrescribe_historial(db):
    _pitcher(db, 1, 100, 20, 0.5)
    db.commit()
    build_league_distributions(db, season=2026, role="pitcher", data_start_date=START, data_end_date=END)
    result = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END,
        distribution_version="mlb-2026-v2",
    )
    assert result.created == 8
    assert db.query(LeagueMetricDistribution).count() == 16


def test_baseline_pondera_oportunidades_sin_alterar_distribucion(db):
    _pitcher(db, 1, 50, 20, 1.0)   # zone_rate=.50
    _pitcher(db, 2, 950, 40, 0.0)  # zone_rate=.40
    db.commit()
    build_league_distributions(db, season=2026, role="pitcher", data_start_date=START, data_end_date=END)
    zone = db.query(LeagueMetricDistribution).filter_by(metric="zone_rate").one()
    assert float(zone.population_mean) == 0.45
    assert float(zone.league_baseline) == 0.405
    assert float(zone.p50) == 0.45


def test_velocity_y_whiff_usan_sus_denominadores_elegibles(db):
    eligible = _pitcher(db, 1, 100, 20, 0.5)
    few_pitches = _pitcher(db, 2, 49, 20, 0.8)
    few_swings = _pitcher(db, 3, 100, 20, 0.2)
    few_swings.swings = 19
    few_swings.whiffs = 5
    few_swings.whiff_rate = round(5 / 19, 6)
    few_swings.csw = few_swings.called_strikes + few_swings.whiffs
    few_swings.csw_rate = round(few_swings.csw / few_swings.csw_opportunities, 6)
    db.commit()
    build_league_distributions(db, season=2026, role="pitcher", data_start_date=START, data_end_date=END)

    velocity = db.query(LeagueMetricDistribution).filter_by(metric="avg_velocity").one()
    whiff = db.query(LeagueMetricDistribution).filter_by(metric="whiff_rate").one()
    assert velocity.population_size == 2
    assert velocity.sample_size_total == eligible.pitches + few_swings.pitches
    assert whiff.population_size == 2
    assert whiff.sample_size_total == eligible.swings + few_pitches.swings

    rerun = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END
    )
    assert rerun.unchanged == 8


def test_percentile_de_distribucion_usa_extremos_y_direccion():
    class Distribution:
        minimum = 0
        p05 = 5
        p10 = 10
        p25 = 25
        p50 = 50
        p75 = 75
        p90 = 90
        p95 = 95
        maximum = 100

    distribution = Distribution()
    assert distribution_percentile_rank(0, distribution) == 0
    assert distribution_percentile_rank(50, distribution) == 0.5
    assert distribution_percentile_rank(100, distribution) == 1
    assert distribution_percentile_rank(82.5, distribution) == 0.825
    assert distribution_percentile_rank(25, distribution, direction="lower") == 0.75
    assert percentile_rating(0) == 40
    assert percentile_rating(0.5) == 70
    assert percentile_rating(1) == 99


def test_percentile_rank_colapsa_anclas_repetidas_al_centro_del_empate():
    assert percentile_rank(
        0,
        [(0, 0.00), (0, 0.05), (0, 0.10), (1, 0.25), (1, 0.50), (1, 0.75), (2, 1.00)],
    ) == 0.05
    assert percentile_rank(
        1,
        [(0, 0.00), (0, 0.05), (0, 0.10), (1, 0.25), (1, 0.50), (1, 0.75), (2, 1.00)],
    ) == 0.50


def test_percentile_hbp_con_empate_en_cero_no_produce_p100_inverso():
    class HbpDistribution:
        minimum = 0
        p05 = 0
        p10 = 0
        p25 = 0
        p50 = 0
        p75 = 0
        p90 = 0.03
        p95 = 0.04
        maximum = 0.05

    statistical = distribution_percentile_rank(0, HbpDistribution())
    ability = distribution_percentile_rank(0, HbpDistribution(), direction="lower")
    assert statistical == 0.375
    assert ability == 0.625
    assert ability < 1.0


def test_movement_crea_scope_pitch_type_y_fallback_family(db):
    profiles = [
        _movement_profile(db, 100 + index, "SI", PitchFamily.FASTBALL, 10 + index, 1 + index / 10, 0.5)
        for index in range(10)
    ]
    for index in range(5):
        _movement_profile(db, 200 + index, "FF", PitchFamily.FASTBALL, 20, 0.8, 1.2 + index / 10)
    db.commit()

    result = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END
    )
    sinker = db.query(LeagueMetricDistribution).filter_by(
        metric="movement_magnitude", pitch_type="SI", pitch_family="FASTBALL"
    ).one()
    family = db.query(LeagueMetricDistribution).filter_by(
        metric="movement_magnitude", pitch_type=None, pitch_family="FASTBALL"
    ).one()
    assert sinker.population_size == 10
    assert sinker.sample_size_total == sum(profile.pitch_count for profile in profiles)
    assert family.population_size == 15
    assert abs(float(sinker.minimum) - (1 ** 2 + 0.5 ** 2) ** 0.5) < 1e-8
    assert result.created == 10  # ocho globales + SI + FASTBALL fallback

    rerun = build_league_distributions(
        db, season=2026, role="pitcher", data_start_date=START, data_end_date=END
    )
    assert rerun.unchanged == 10


def test_movement_excluye_poca_muestra_pitchout_y_splits(db):
    base = _movement_profile(db, 1, "SI", PitchFamily.FASTBALL, 9, 1.5, 0.4)
    db.add(PitcherPitchProfile(
        player_season_id=base.player_season_id,
        pitch_type="SI", pitch_family=PitchFamily.FASTBALL, batter_side=SplitHand.LEFT,
        pitch_count=20, sample_size=20, usage_rate=1, avg_pfx_x=1.5, avg_pfx_z=0.4,
    ))
    _movement_profile(db, 2, "PO", PitchFamily.OTHER, 20, 1.0, 1.0)
    db.commit()
    build_league_distributions(db, season=2026, role="pitcher", data_start_date=START, data_end_date=END)
    assert db.query(LeagueMetricDistribution).filter_by(metric="movement_magnitude").count() == 0


def test_fallback_family_agrega_pitch_types_antes_de_contar_pitchers(db):
    pitcher_a = _movement_profile(db, 1, "FF", PitchFamily.FASTBALL, 20, 1.0, 0.0)
    db.add(PitcherPitchProfile(
        player_season_id=pitcher_a.player_season_id,
        pitch_type="SI", pitch_family=PitchFamily.FASTBALL, batter_side=SplitHand.ALL,
        pitch_count=30, sample_size=30, usage_rate=0.6, avg_pfx_x=2.0, avg_pfx_z=0.0,
    ))
    for index in range(14):
        _movement_profile(db, 100 + index, "FF", PitchFamily.FASTBALL, 40, 1.0, 0.0)
    db.commit()

    build_league_distributions(db, season=2026, role="pitcher", data_start_date=START, data_end_date=END)
    family = db.query(LeagueMetricDistribution).filter_by(
        metric="movement_magnitude", pitch_type=None, pitch_family="FASTBALL"
    ).one()
    # Pitcher A aporta (1*20 + 2*30)/50 = 1.6 como una sola observación.
    assert family.population_size == 15
    assert family.sample_size_total == 610
    assert abs(float(family.population_mean) - 1.04) < 1e-8
    assert abs(float(family.league_baseline) - (640 / 610)) < 1e-8
