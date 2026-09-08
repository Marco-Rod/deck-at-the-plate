"""Operación común MomentEvaluation → PlayerRatings D-1 → perfil."""

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
    CardRatingProfile,
    MomentContext,
    MomentContextSourceType,
    MomentEvaluation,
    MomentType,
    Player,
    PlayerRatings,
)
from etl.services.moment_profile_pipeline import (
    generate_profile_for_moment_evaluation,
)


GAME_DATE = dt.date(2026, 8, 30)
SEASON_START = dt.date(2026, 3, 25)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _scenario(db, *, moment_type=MomentType.MULTI_HR_GAME, with_ratings=True):
    player = Player(mlb_id=100, full_name="Moment Player")
    edition = CardEdition(
        code=f"2026_{moment_type.value}_100",
        name=moment_type.value,
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference="mlb-game:900001:batter:100",
        metadata_payload={},
    )
    db.add_all([player, edition])
    db.flush()
    facts = {
        "game": {"game_pk": 900001, "game_date": GAME_DATE.isoformat()},
        "batting": {"hits": 4, "home_runs": 3, "runs_batted_in": 6},
        "home_runs": [{}, {}, {}],
    }
    if moment_type == MomentType.WALK_OFF_HR:
        facts = {
            "schedule_candidate": {"game_date": GAME_DATE.isoformat()},
            "game": {"game_pk": 900001},
            "batting": {
                "hits": 2,
                "home_runs": 1,
                "runs_batted_in": 2,
                "walk_off": True,
            },
        }
    context = MomentContext(
        player_id=player.id,
        card_edition_id=edition.id,
        role="BATTER",
        season=2026,
        occurred_at=dt.datetime(2026, 8, 31, tzinfo=dt.timezone.utc),
        source_type=MomentContextSourceType.MLB_STATS_API,
        source_reference="mlb-stats-api:game/900001/feed/live",
        context_version="moment-context-1.0",
        facts=facts,
        input_hash="c" * 64,
    )
    db.add(context)
    db.flush()
    evaluation = MomentEvaluation(
        moment_context_id=context.id,
        moment_type=moment_type,
        significance_score=Decimal("0.80058"),
        performance_score=Decimal("0.91500"),
        leverage_score=Decimal("0.31667"),
        statistical_uncommonness=Decimal("0.93000"),
        evaluation_version="moment-eval-1.0",
        rules_payload={},
        input_hash="e" * 64,
    )
    db.add(evaluation)
    ratings = None
    if with_ratings:
        ratings = PlayerRatings(
            player_id=player.id,
            season=2026,
            role="BATTER",
            rating_model_version="ratings-2.0",
            distribution_version="dist-1.0",
            data_start_date=SEASON_START,
            data_end_date=GAME_DATE - dt.timedelta(days=1),
            contact_rating=70,
            power_rating=72,
            vision_rating=68,
            clutch_rating=70,
            overall_rating=70,
            input_hash="r" * 64,
        )
        db.add(ratings)
    db.commit()
    return evaluation, ratings


@pytest.mark.parametrize(
    "moment_type", (MomentType.WALK_OFF_HR, MomentType.MULTI_HR_GAME)
)
def test_genera_ambos_tipos_con_el_snapshot_d_menos_uno(db, moment_type):
    evaluation, ratings = _scenario(db, moment_type=moment_type)

    result = generate_profile_for_moment_evaluation(
        db, evaluation=evaluation
    )

    assert result.status == "CREATED"
    assert result.source_player_ratings_id == ratings.id
    assert result.card_rating_profile_id is not None
    assert db.query(CardRatingProfile).count() == 1


def test_falta_de_ratings_devuelve_skip_explicito(db):
    evaluation, _ = _scenario(db, with_ratings=False)

    result = generate_profile_for_moment_evaluation(
        db, evaluation=evaluation
    )

    assert result.status == "SKIPPED_NO_RATINGS"
    assert result.card_rating_profile_id is None
    assert result.source_player_ratings_id is None
    assert db.query(CardRatingProfile).count() == 0


def test_commit_false_respeta_savepoint_del_caller(db):
    evaluation, _ = _scenario(db)

    with pytest.raises(RuntimeError):
        with db.begin_nested():
            generate_profile_for_moment_evaluation(
                db, evaluation=evaluation, commit=False
            )
            raise RuntimeError("rollback savepoint")

    assert db.query(CardRatingProfile).count() == 0
