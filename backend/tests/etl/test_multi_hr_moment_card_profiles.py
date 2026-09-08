"""Generación batch de CardRatingProfile para MULTI_HR_GAME."""

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
from etl.cli import _build_parser
from etl.services.multi_hr_moment_card_profiles import (
    generate_multi_hr_moment_card_profiles,
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


def _seed(db, mlb_id, *, ratings_end=None):
    player = Player(mlb_id=mlb_id, full_name=f"Player {mlb_id}")
    edition = CardEdition(
        code=f"2026_MULTI_HR_GAME_{mlb_id}",
        name="Multi-Home Run Game",
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference=f"mlb-game:900001:batter:{mlb_id}",
        metadata_payload={},
    )
    db.add_all([player, edition])
    db.flush()
    context = MomentContext(
        player_id=player.id,
        card_edition_id=edition.id,
        role="BATTER",
        season=2026,
        occurred_at=dt.datetime(2026, 8, 31, tzinfo=dt.timezone.utc),
        source_type=MomentContextSourceType.MLB_STATS_API,
        source_reference=f"mlb-stats-api:game/900001:batter/{mlb_id}",
        context_version="moment-context-1.0",
        facts={
            "game": {"game_pk": 900001, "game_date": GAME_DATE.isoformat()},
            "batting": {"hits": 4, "home_runs": 3, "runs_batted_in": 6},
            "home_runs": [{}, {}, {}],
        },
        input_hash=str(mlb_id)[-1] * 64,
    )
    db.add(context)
    db.flush()
    evaluation = MomentEvaluation(
        moment_context_id=context.id,
        moment_type=MomentType.MULTI_HR_GAME,
        significance_score=Decimal("0.80058"),
        performance_score=Decimal("0.91500"),
        leverage_score=Decimal("0.31667"),
        statistical_uncommonness=Decimal("0.93000"),
        evaluation_version="moment-eval-1.0",
        rules_payload={},
        input_hash=("e" if mlb_id == 100 else "f") * 64,
    )
    db.add(evaluation)
    ratings = None
    if ratings_end is not None:
        ratings = PlayerRatings(
            player_id=player.id,
            season=2026,
            role="BATTER",
            rating_model_version="ratings-2.0",
            distribution_version="dist-1.0",
            data_start_date=SEASON_START,
            data_end_date=ratings_end,
            contact_rating=70,
            power_rating=72,
            vision_rating=68,
            clutch_rating=70,
            overall_rating=70,
            input_hash=("r" if mlb_id == 100 else "s") * 64,
        )
        db.add(ratings)
    db.commit()
    return player, evaluation, ratings


def test_resuelve_d_menos_uno_genera_perfil_y_rerun_es_unchanged(db):
    _, _, prior = _seed(db, 100, ratings_end=GAME_DATE - dt.timedelta(days=1))
    _seed(db, 200, ratings_end=None)

    first = generate_multi_hr_moment_card_profiles(db)
    second = generate_multi_hr_moment_card_profiles(db)

    assert (first.selected, first.created, first.skipped_no_ratings) == (2, 1, 1)
    assert (second.selected, second.unchanged, second.skipped_no_ratings) == (
        2,
        1,
        1,
    )
    profile = db.query(CardRatingProfile).one()
    assert profile.source_player_ratings_id == prior.id
    assert (
        profile.contact_rating,
        profile.power_rating,
        profile.vision_rating,
        profile.clutch_rating,
        profile.overall_rating,
    ) == (77, 89, 70, 74, 78)


def test_snapshot_del_mismo_dia_no_es_usable(db):
    _seed(db, 100, ratings_end=GAME_DATE)

    result = generate_multi_hr_moment_card_profiles(db)

    assert result.skipped_no_ratings == 1
    assert db.query(CardRatingProfile).count() == 0


def test_cli_expone_generacion_sin_recalcular_ratings():
    args = _build_parser().parse_args(
        ["generate-multi-hr-moment-card-profiles"]
    )
    assert args.command == "generate-multi-hr-moment-card-profiles"
