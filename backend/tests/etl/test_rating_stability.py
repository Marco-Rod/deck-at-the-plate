import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, PlayerRatings
from etl.services.rating_stability import (
    audit_rating_stability,
    select_fractional_snapshots,
)


START = dt.date(2026, 3, 25)
FINAL = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _ratings(db, player, end, rating, evidence):
    row = PlayerRatings(
        player_id=player.id,
        season=2026,
        role="BATTER",
        rating_model_version="ratings-2.0",
        distribution_version="dist-1.0",
        data_start_date=START,
        data_end_date=end,
        contact_rating=rating,
        power_rating=rating,
        vision_rating=rating,
        clutch_rating=70,
        overall_rating=rating,
        contact_evidence=evidence,
        power_evidence=evidence,
        vision_evidence=evidence,
        input_hash=(str(end.toordinal()) * 64)[:64],
    )
    db.add(row)


def test_selects_nearest_distinct_fractional_snapshots():
    dates = (
        dt.date(2026, 5, 1),
        dt.date(2026, 6, 15),
        dt.date(2026, 7, 25),
    )
    assert select_fractional_snapshots(
        dates, data_start_date=START, final_date=FINAL
    ) == dates


def test_audit_groups_error_by_attribute_and_evidence_without_writes(db):
    player = Player(mlb_id=1, full_name="Example", primary_position="1B")
    db.add(player)
    db.flush()
    snapshot = dt.date(2026, 6, 15)
    _ratings(db, player, snapshot, 70, Decimal("0.25"))
    _ratings(db, player, FINAL, 76, Decimal("0.75"))
    db.commit()

    audit = audit_rating_stability(
        db,
        season=2026,
        data_start_date=START,
        final_date=FINAL,
        snapshot_dates=(snapshot,),
    )

    assert audit.final_players == 1
    assert audit.matched_player_snapshots == 1
    assert audit.next_matched_player_snapshots == 1
    assert len(audit.buckets) == 6
    final_buckets = [row for row in audit.buckets if row.comparison == "FINAL"]
    assert {row.attribute for row in final_buckets} == {"contact", "power", "vision"}
    assert all(row.evidence_bucket == "0.20-0.29" for row in final_buckets)
    assert all(row.mae == Decimal("6.00") for row in final_buckets)
    assert all(row.within_5_pct == Decimal("0.00") for row in final_buckets)
    assert all(row.within_10_pct == Decimal("100.00") for row in final_buckets)
    threshold = next(
        row for row in audit.thresholds
        if row.comparison == "FINAL"
        and row.attribute == "power"
        and row.minimum_evidence == Decimal("0.20")
    )
    assert threshold.observations == 1
    assert threshold.players == 1
    assert threshold.p90_error == Decimal("6.00")
    assert threshold.p90_ci_low == Decimal("6.00")
    assert threshold.within_5_ci_high == Decimal("0.00")
    assert db.query(PlayerRatings).count() == 2


def test_requires_earlier_snapshot(db):
    player = Player(mlb_id=2, full_name="Final Only", primary_position="P")
    db.add(player)
    db.flush()
    _ratings(db, player, FINAL, 70, Decimal("0.50"))
    db.commit()

    with pytest.raises(ValueError, match="no earlier"):
        audit_rating_stability(
            db, season=2026, data_start_date=START, final_date=FINAL
        )


def test_next_snapshot_separates_short_horizon_from_final_horizon(db):
    player = Player(mlb_id=3, full_name="Changing", primary_position="1B")
    db.add(player)
    db.flush()
    first = dt.date(2026, 5, 4)
    second = dt.date(2026, 6, 13)
    _ratings(db, player, first, 60, Decimal("0.50"))
    _ratings(db, player, second, 70, Decimal("0.50"))
    _ratings(db, player, FINAL, 90, Decimal("0.90"))
    db.commit()

    audit = audit_rating_stability(
        db,
        season=2026,
        data_start_date=START,
        final_date=FINAL,
        snapshot_dates=(first, second),
        bootstrap_iterations=20,
    )
    final = next(
        row for row in audit.thresholds
        if row.comparison == "FINAL"
        and row.attribute == "power"
        and row.minimum_evidence == Decimal("0.50")
    )
    following = next(
        row for row in audit.thresholds
        if row.comparison == "NEXT"
        and row.attribute == "power"
        and row.minimum_evidence == Decimal("0.50")
    )

    assert final.mae == Decimal("25.00")
    assert following.mae == Decimal("15.00")
    assert final.p90_error == Decimal("29.00")
    assert following.p90_error == Decimal("19.00")
