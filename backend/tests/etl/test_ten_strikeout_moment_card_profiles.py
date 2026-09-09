"""Vertical slice D-1 para perfiles MOMENT de juegos con 10+ K."""

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
from etl.services.ten_strikeout_moment_card_profiles import (
    generate_ten_strikeout_moment_card_profiles,
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


def _seed_gavin(db, *, ratings_end):
    player = Player(mlb_id=806270, full_name="Gavin Williams")
    edition = CardEdition(
        code="2026_10_STRIKEOUT_GAME_806270_900010",
        name="13-Strikeout Game",
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference="mlb-game:900010:pitcher:806270",
        metadata_payload={},
    )
    db.add_all([player, edition])
    db.flush()
    context = MomentContext(
        player_id=player.id,
        card_edition_id=edition.id,
        role="PITCHER",
        season=2026,
        occurred_at=dt.datetime(2026, 8, 31, tzinfo=dt.timezone.utc),
        source_type=MomentContextSourceType.MLB_STATS_API,
        source_reference="mlb-stats-api:game/900010:pitcher/806270",
        context_version="moment-context-1.0",
        facts={
            "game": {"game_pk": 900010, "game_date": GAME_DATE.isoformat()},
            "pitching": {"strikeouts": 13},
        },
        input_hash="c" * 64,
    )
    db.add(context)
    db.flush()
    evaluation = MomentEvaluation(
        moment_context_id=context.id,
        moment_type=MomentType.TEN_STRIKEOUT_GAME,
        significance_score=Decimal(".92370"),
        performance_score=Decimal(".91450"),
        leverage_score=Decimal(".50000"),
        statistical_uncommonness=Decimal("1.00000"),
        evaluation_version="moment-eval-1.0",
        rules_payload={},
        input_hash="e" * 64,
    )
    ratings = PlayerRatings(
        player_id=player.id,
        season=2026,
        role="PITCHER",
        rating_model_version="ratings-2.0",
        distribution_version="dist-1.0",
        data_start_date=SEASON_START,
        data_end_date=ratings_end,
        velocity_rating=76,
        control_rating=78,
        movement_rating=69,
        stuff_rating=89,
        overall_rating=79,
        input_hash="r" * 64,
    )
    db.add_all([evaluation, ratings])
    db.commit()
    return evaluation, ratings


def test_genera_perfil_pitcher_con_snapshot_d_menos_uno_y_es_idempotente(db):
    _, ratings = _seed_gavin(
        db, ratings_end=GAME_DATE - dt.timedelta(days=1)
    )

    first = generate_ten_strikeout_moment_card_profiles(db)
    second = generate_ten_strikeout_moment_card_profiles(db)

    assert (first.selected, first.created, first.failed) == (1, 1, 0)
    assert (second.selected, second.unchanged, second.failed) == (1, 1, 0)
    profile = db.query(CardRatingProfile).one()
    assert profile.source_player_ratings_id == ratings.id
    assert ratings.data_end_date == GAME_DATE - dt.timedelta(days=1)
    assert (
        profile.velocity_rating,
        profile.control_rating,
        profile.movement_rating,
        profile.stuff_rating,
        profile.overall_rating,
    ) == (81, 85, 76, 99, 85)
    metadata = profile.metadata_payload["calculation_metadata"]
    policy = metadata["rating_adjustment_policy"]
    assert policy["requested_adjustments"]["stuff_rating"] == 12
    assert policy["applied_adjustments"]["stuff_rating"] == 10
    assert policy["capped_attributes"] == ["stuff_rating"]


def test_snapshot_del_mismo_dia_no_es_usable(db):
    _seed_gavin(db, ratings_end=GAME_DATE)

    result = generate_ten_strikeout_moment_card_profiles(db)

    assert result.skipped_no_ratings == 1
    assert db.query(CardRatingProfile).count() == 0


def test_cli_expone_generacion_generica_de_perfiles_10_k():
    args = _build_parser().parse_args(
        ["generate-ten-strikeout-moment-card-profiles"]
    )
    assert args.command == "generate-ten-strikeout-moment-card-profiles"
