"""Pruebas de shrinkage y resolución de scopes para Movement ratings-2.0."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.enums import PitchFamily, SplitHand
from app.database import Base
from app.models import LeagueMetricDistribution, PitcherPitchProfile, Player, PlayerSeason
from etl.services.pitcher_movement import calculate_movement_candidate


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


def _distribution(db, pitch_type, family, baseline):
    db.add(LeagueMetricDistribution(
        season=2026, role="PITCHER", metric="movement_magnitude",
        pitch_type=pitch_type, pitch_family=family, population_size=20, sample_size_total=500,
        population_mean=1, league_baseline=baseline, median=1, stddev=0.5,
        minimum=0, p05=0.1, p10=0.2, p25=0.5, p50=1, p75=1.5,
        p90=1.8, p95=1.9, maximum=2, distribution_version="dist-1.0",
        data_start_date=START, data_end_date=END,
    ))


def _profile(db, ps, pitch_type, family, count, usage, x, z):
    db.add(PitcherPitchProfile(
        player_season_id=ps.id, pitch_type=pitch_type, pitch_family=family,
        batter_side=SplitHand.ALL, pitch_count=count, sample_size=count,
        usage_rate=usage, avg_pfx_x=x, avg_pfx_z=z,
    ))


def _seed_player(db):
    player = Player(mlb_id=650911, full_name="Cristopher Sanchez", primary_position="SP")
    db.add(player)
    db.flush()
    ps = PlayerSeason(player_id=player.id, season=2026, data_start_date=START, data_end_date=END)
    db.add(ps)
    db.flush()
    return ps


def test_resuelve_type_luego_family_aplica_shrinkage_y_renormaliza(db):
    ps = _seed_player(db)
    _profile(db, ps, "SI", PitchFamily.FASTBALL, 50, 0.50, 2, 0)
    _profile(db, ps, "FS", PitchFamily.OFFSPEED, 25, 0.25, 1, 0)
    _profile(db, ps, "KC", PitchFamily.BREAKING, 25, 0.25, 1, 0)
    _distribution(db, "SI", "FASTBALL", 1)
    _distribution(db, None, "FASTBALL", 0.2)  # No debe ganar al scope SI.
    _distribution(db, None, "OFFSPEED", 2)
    db.commit()

    result = calculate_movement_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    by_type = {pitch.pitch_type: pitch for pitch in result.pitches}
    assert by_type["SI"].scope == "pitch_type"
    assert by_type["SI"].shrinkage_weight == 0.5
    assert by_type["SI"].adjusted_magnitude == 1.5
    assert by_type["SI"].rating == 84
    assert by_type["FS"].scope == "pitch_family"
    assert abs(by_type["FS"].shrinkage_weight - 1 / 3) < 1e-12
    assert abs(by_type["FS"].adjusted_magnitude - 5 / 3) < 1e-12
    assert result.skipped_pitch_types == ["KC"]
    assert result.evaluable_usage == 0.75
    expected = round((by_type["SI"].rating * 0.50 + by_type["FS"].rating * 0.25) / 0.75)
    assert result.movement_rating == expected
    assert result.rating_model_version == "ratings-2.0"


def test_sin_scope_confiable_no_asigna_rating_neutral(db):
    ps = _seed_player(db)
    _profile(db, ps, "KC", PitchFamily.BREAKING, 14, 1, 1, 1)
    db.commit()
    result = calculate_movement_candidate(
        db, mlb_id=650911, season=2026, data_start_date=START, data_end_date=END
    )
    assert result.movement_rating is None
    assert result.pitches == []
    assert result.skipped_pitch_types == ["KC"]
