"""Evaluación V1 de 10_STRIKEOUT_GAME sin producir ajustes ni ratings."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    MomentContextSourceType,
    MomentEvaluation,
    MomentType,
    Player,
)
from etl.cli import _build_parser
from etl.services.moment_contexts import persist_moment_context
from etl.services.moment_evaluations import evaluate_moment
from etl.services.ten_strikeout_moment_evaluations import (
    evaluate_discovered_ten_strikeout_moments,
)


OCCURRED_AT = dt.datetime(2026, 9, 1, 2, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _context(
    db,
    mlb_id,
    *,
    innings_pitched,
    outs_recorded,
    strikeouts,
    batters_faced,
    earned_runs,
    strikeout_play_count=None,
):
    player = Player(mlb_id=mlb_id, full_name=f"Pitcher {mlb_id}")
    edition = CardEdition(
        code=f"2026_10_STRIKEOUT_GAME_{mlb_id}",
        name="10-Strikeout Game",
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference=f"mlb-game:900010:pitcher:{mlb_id}",
        metadata_payload={},
    )
    db.add_all([player, edition])
    db.commit()
    play_count = (
        strikeouts if strikeout_play_count is None else strikeout_play_count
    )
    persisted = persist_moment_context(
        db,
        player_id=player.id,
        card_edition_id=edition.id,
        role="PITCHER",
        occurred_at=OCCURRED_AT,
        source_type=MomentContextSourceType.MLB_STATS_API,
        source_reference=f"mlb-stats-api:game/900010:pitcher/{mlb_id}",
        facts={
            "game": {"game_pk": 900010, "game_date": "2026-08-31"},
            "pitching": {
                "innings_pitched": innings_pitched,
                "outs_recorded": outs_recorded,
                "strikeouts": strikeouts,
                "batters_faced": batters_faced,
                "hits": 4,
                "walks": 1,
                "earned_runs": earned_runs,
                "pitches": 100,
                "strikes": 68,
                "team_side": "AWAY",
                "game_result": "WON",
            },
            "strikeouts": [{} for _ in range(play_count)],
        },
    )
    return persisted.moment_context_id


def test_williams_like_es_elite_por_k_rate_y_cero_er(db):
    context_id = _context(
        db,
        111,
        innings_pitched="7.0",
        outs_recorded=21,
        strikeouts=13,
        batters_faced=25,
        earned_runs=0,
    )

    result = evaluate_moment(db, moment_context_id=context_id)

    assert result.moment_type == MomentType.TEN_STRIKEOUT_GAME
    assert result.performance_score == Decimal("0.91450")
    assert result.statistical_uncommonness == Decimal("1.00000")
    assert result.leverage_score == Decimal("0.50000")
    assert result.significance_score == Decimal("0.92370")


def test_sale_like_reconoce_nueve_ip_y_shutout(db):
    context_id = _context(
        db,
        112,
        innings_pitched="9.0",
        outs_recorded=27,
        strikeouts=11,
        batters_faced=34,
        earned_runs=0,
    )

    result = evaluate_moment(db, moment_context_id=context_id)

    assert result.performance_score == Decimal("0.77412")
    assert result.statistical_uncommonness == Decimal("0.95000")
    assert result.significance_score == Decimal("0.82197")


def test_bradley_like_con_cuatro_er_sigue_premiando_once_k(db):
    context_id = _context(
        db,
        113,
        innings_pitched="6.2",
        outs_recorded=20,
        strikeouts=11,
        batters_faced=28,
        earned_runs=4,
    )

    result = evaluate_moment(db, moment_context_id=context_id)

    assert result.performance_score == Decimal("0.59571")
    assert result.statistical_uncommonness == Decimal("0.80000")
    assert result.significance_score == Decimal("0.66243")


def test_exactamente_diez_k_es_evaluable(db):
    context_id = _context(
        db,
        114,
        innings_pitched="7.0",
        outs_recorded=21,
        strikeouts=10,
        batters_faced=23,
        earned_runs=0,
    )

    result = evaluate_moment(db, moment_context_id=context_id)

    assert result.status == "CREATED"
    assert result.performance_score == Decimal("0.77337")
    assert result.statistical_uncommonness == Decimal("0.75000")
    assert result.significance_score == Decimal("0.75152")


def test_catorce_k_hace_clamp_en_k_y_uncommonness(db):
    context_id = _context(
        db,
        115,
        innings_pitched="7.0",
        outs_recorded=21,
        strikeouts=14,
        batters_faced=26,
        earned_runs=1,
    )

    result = evaluate_moment(db, moment_context_id=context_id)
    evaluation = db.get(MomentEvaluation, result.moment_evaluation_id)

    assert result.statistical_uncommonness == Decimal("1.00000")
    assert result.performance_score <= Decimal("1.00000")
    assert evaluation.rules_payload["strikeout_score_base"] == "0.60"


@pytest.mark.parametrize(
    "innings_pitched,outs_recorded,strikeout_play_count",
    [("6.2", 19, 10), ("6.3", 21, 10), ("6.2", 20, 9)],
)
def test_rechaza_hechos_inconsistentes(
    db, innings_pitched, outs_recorded, strikeout_play_count
):
    context_id = _context(
        db,
        116,
        innings_pitched=innings_pitched,
        outs_recorded=outs_recorded,
        strikeouts=10,
        batters_faced=25,
        earned_runs=1,
        strikeout_play_count=strikeout_play_count,
    )

    with pytest.raises(ValueError):
        evaluate_moment(db, moment_context_id=context_id)


def test_batch_es_idempotente_y_cli_no_toca_ratings(db):
    _context(
        db,
        117,
        innings_pitched="6.2",
        outs_recorded=20,
        strikeouts=10,
        batters_faced=25,
        earned_runs=1,
    )

    first = evaluate_discovered_ten_strikeout_moments(db)
    second = evaluate_discovered_ten_strikeout_moments(db)
    args = _build_parser().parse_args(["evaluate-ten-strikeout-moments"])

    assert (first.selected, first.created, first.failed) == (1, 1, 0)
    assert (second.selected, second.unchanged, second.failed) == (1, 1, 0)
    assert first.moment_evaluation_ids == second.moment_evaluation_ids
    assert db.query(MomentEvaluation).count() == 1
    assert args.command == "evaluate-ten-strikeout-moments"
