"""Vertical slice MomentEvaluation → ajustes → policy → CardRatingProfile."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
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
from etl.services.moment_card_profiles import generate_moment_card_rating_profile


START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _scenario(db):
    player = Player(mlb_id=660271, full_name="Moment Batter")
    edition = CardEdition(
        code="2026_WALK_OFF_001",
        name="Walk-Off Hero",
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference="mlb-game:824230",
        metadata_payload={"game_pk": 824230},
    )
    db.add_all([player, edition])
    db.flush()
    ratings = PlayerRatings(
        player_id=player.id,
        season=2026,
        role="BATTER",
        rating_model_version="ratings-2.0",
        distribution_version="dist-1.0",
        data_start_date=START,
        data_end_date=END,
        contact_rating=70,
        power_rating=72,
        vision_rating=68,
        clutch_rating=70,
        overall_rating=70,
        input_hash="r" * 64,
    )
    context = MomentContext(
        player_id=player.id,
        card_edition_id=edition.id,
        role="BATTER",
        season=2026,
        occurred_at=dt.datetime(2026, 9, 5, 21, 15, tzinfo=dt.timezone.utc),
        source_type=MomentContextSourceType.STATCAST,
        source_reference="statcast:824230:660271",
        context_version="moment-context-1.0",
        facts={
            "game": {"game_pk": 824230},
            "batting": {
                "hits": 4,
                "home_runs": 2,
                "runs_batted_in": 5,
                "walk_off": True,
            },
        },
        input_hash="c" * 64,
    )
    db.add_all([ratings, context])
    db.flush()
    evaluation = MomentEvaluation(
        moment_context_id=context.id,
        moment_type=MomentType.WALK_OFF_HR,
        significance_score=Decimal("0.70"),
        performance_score=Decimal("0.50"),
        leverage_score=Decimal("1.00"),
        statistical_uncommonness=Decimal("0.70"),
        evaluation_version="moment-eval-1.0",
        rules_payload={"fixture": "walk-off-hr"},
        input_hash="e" * 64,
    )
    db.add(evaluation)
    db.commit()
    return player, edition, ratings, context, evaluation


def test_genera_perfil_moment_end_to_end_sin_mutar_player_ratings(db):
    _, _, ratings, _, evaluation = _scenario(db)
    base_values = (
        ratings.contact_rating,
        ratings.power_rating,
        ratings.vision_rating,
        ratings.clutch_rating,
        ratings.input_hash,
    )

    result = generate_moment_card_rating_profile(
        db,
        moment_evaluation_id=evaluation.id,
        source_player_ratings_id=ratings.id,
    )
    profile = db.get(CardRatingProfile, result.card_rating_profile_id)

    assert result.status == "CREATED"
    assert (result.adjustments.contact, result.adjustments.power) == (5, 10)
    assert (result.adjustments.vision, result.adjustments.clutch) == (2, 15)
    assert (
        profile.contact_rating,
        profile.power_rating,
        profile.vision_rating,
        profile.clutch_rating,
    ) == (75, 82, 70, 85)
    assert profile.overall_rating == 77
    assert base_values == (
        ratings.contact_rating,
        ratings.power_rating,
        ratings.vision_rating,
        ratings.clutch_rating,
        ratings.input_hash,
    )


def test_metadata_reconstruye_toda_la_cadena(db):
    _, _, ratings, context, evaluation = _scenario(db)
    result = generate_moment_card_rating_profile(
        db,
        moment_evaluation_id=evaluation.id,
        source_player_ratings_id=ratings.id,
    )
    metadata = db.get(
        CardRatingProfile, result.card_rating_profile_id
    ).metadata_payload
    calculation = metadata["calculation_metadata"]

    assert calculation["calculation_chain"] == [
        "MomentContext",
        "MomentEvaluation",
        "MomentRatingAdjustmentPolicy",
        "MomentPolicy",
        "CardRatingProfile",
    ]
    assert calculation["moment_context"]["id"] == context.id
    assert calculation["moment_context"]["facts"] == context.facts
    assert calculation["moment_evaluation"]["id"] == evaluation.id
    assert calculation["moment_evaluation"]["rules"] == evaluation.rules_payload
    adjustment = calculation["rating_adjustment_policy"]
    assert adjustment["requested_adjustments"]["power_rating"] == 10
    assert adjustment["applied_adjustments"]["clutch_rating"] == 15
    assert adjustment["policy_version"] == "moment-rating-adjustment-1.0"
    assert metadata["transformation"] == "MOMENT_POLICY"
    assert metadata["overall_policy"]["policy_version"] == "card-overall-1.0"
    assert metadata["overall_policy"]["source"] == "FINAL_CARD_RATINGS"
    assert metadata["overall_policy"]["raw_score"] == "77.35"
    assert metadata["overall_policy"]["rating"] == 77
    assert metadata["source_player_ratings"]["id"] == ratings.id


def test_repeticion_es_unchanged(db):
    _, _, ratings, _, evaluation = _scenario(db)
    created = generate_moment_card_rating_profile(
        db,
        moment_evaluation_id=evaluation.id,
        source_player_ratings_id=ratings.id,
    )
    unchanged = generate_moment_card_rating_profile(
        db,
        moment_evaluation_id=evaluation.id,
        source_player_ratings_id=ratings.id,
    )

    assert unchanged.status == "UNCHANGED"
    assert unchanged.card_rating_profile_id == created.card_rating_profile_id
    assert unchanged.input_hash == created.input_hash
    assert db.query(CardRatingProfile).count() == 1


def test_multi_hr_usa_policy_power_oriented_y_recalcula_overall(db):
    _, _, ratings, _, evaluation = _scenario(db)
    evaluation.moment_type = MomentType.MULTI_HR_GAME
    evaluation.performance_score = Decimal("0.91500")
    evaluation.statistical_uncommonness = Decimal("0.93000")
    evaluation.leverage_score = Decimal("0.31667")
    evaluation.significance_score = Decimal("0.80058")
    evaluation.input_hash = "m" * 64
    db.commit()

    result = generate_moment_card_rating_profile(
        db,
        moment_evaluation_id=evaluation.id,
        source_player_ratings_id=ratings.id,
    )
    profile = db.get(CardRatingProfile, result.card_rating_profile_id)

    assert (result.adjustments.contact, result.adjustments.power) == (7, 17)
    assert (result.adjustments.vision, result.adjustments.clutch) == (2, 4)
    assert (
        profile.contact_rating,
        profile.power_rating,
        profile.vision_rating,
        profile.clutch_rating,
        profile.overall_rating,
    ) == (77, 89, 70, 74, 78)
    assert result.adjustments.reason == "MULTI_HR_GAME"
    metadata = profile.metadata_payload["calculation_metadata"]
    assert metadata["rating_adjustment_policy"]["requested_adjustments"][
        "power_rating"
    ] == 17


def test_cambio_de_evaluacion_actualiza_aunque_redondee_a_mismos_deltas(db):
    _, _, ratings, _, evaluation = _scenario(db)
    created = generate_moment_card_rating_profile(
        db,
        moment_evaluation_id=evaluation.id,
        source_player_ratings_id=ratings.id,
    )
    original_adjustments = created.adjustments.applied_adjustments

    evaluation.significance_score = Decimal("0.80")
    evaluation.input_hash = "f" * 64
    db.commit()
    updated = generate_moment_card_rating_profile(
        db,
        moment_evaluation_id=evaluation.id,
        source_player_ratings_id=ratings.id,
    )

    assert updated.status == "UPDATED"
    assert updated.card_rating_profile_id == created.card_rating_profile_id
    assert updated.input_hash != created.input_hash
    assert updated.adjustments.applied_adjustments == original_adjustments
