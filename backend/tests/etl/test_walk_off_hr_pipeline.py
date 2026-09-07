"""Orquestación del vertical slice WALK_OFF_HR."""

import datetime as dt

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
    Player,
    PlayerRatings,
)
from etl.services.walk_off_hr_detector import (
    WalkOffHrDetectionFailure,
    WalkOffHrDetectionResult,
)
from etl.services.walk_off_hr_pipeline import run_walk_off_hr_pipeline


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


def _seed_context(db, *, mlb_id=660271, with_ratings=True):
    player = Player(mlb_id=mlb_id, full_name=f"Moment Batter {mlb_id}")
    edition = CardEdition(
        code=f"2026_WALK_OFF_HR_{mlb_id}",
        name="Walk-Off Home Run",
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference=f"mlb-game:824230:batter:{mlb_id}",
    )
    db.add_all([player, edition])
    db.flush()
    context = MomentContext(
        player_id=player.id,
        card_edition_id=edition.id,
        role="BATTER",
        season=2026,
        occurred_at=dt.datetime(2026, 9, 2, 23, 30, tzinfo=dt.timezone.utc),
        source_type=MomentContextSourceType.MLB_STATS_API,
        source_reference="mlb-stats-api:game/824230/feed/live",
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
        input_hash=(str(mlb_id)[-1] * 64),
    )
    db.add(context)
    if with_ratings:
        db.add(
            PlayerRatings(
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
                input_hash=("r" if mlb_id == 660271 else "s") * 64,
            )
        )
    db.commit()
    return player, context


def _detection(*context_ids, created=1, unchanged=0, failures=()):
    return WalkOffHrDetectionResult(
        selected=len(context_ids),
        confirmed=len(context_ids),
        created=created,
        updated=0,
        unchanged=unchanged,
        unconfirmed=0,
        failed=sum(failure.kind == "FAILED" for failure in failures),
        moment_context_ids=tuple(context_ids),
        failures=tuple(failures),
    )


def test_orquesta_servicios_y_crea_evaluacion_y_perfil(db, monkeypatch):
    _, context = _seed_context(db)
    monkeypatch.setattr(
        "etl.services.walk_off_hr_pipeline.detect_walk_off_home_runs",
        lambda *_args, **_kwargs: _detection(context.id),
    )

    result = run_walk_off_hr_pipeline(
        db, object(), date_from=START, date_to=END
    )

    assert (result.candidates, result.confirmed, result.contexts_created) == (1, 1, 1)
    assert (result.evaluated, result.evaluations_created) == (1, 1)
    assert (result.profiles_created, result.failed) == (1, 0)
    assert db.query(MomentEvaluation).count() == 1
    assert db.query(CardRatingProfile).count() == 1


def test_segunda_corrida_es_completamente_idempotente(db, monkeypatch):
    _, context = _seed_context(db)
    detections = iter((_detection(context.id), _detection(context.id, created=0, unchanged=1)))
    monkeypatch.setattr(
        "etl.services.walk_off_hr_pipeline.detect_walk_off_home_runs",
        lambda *_args, **_kwargs: next(detections),
    )
    first = run_walk_off_hr_pipeline(db, object(), date_from=START, date_to=END)
    second = run_walk_off_hr_pipeline(db, object(), date_from=START, date_to=END)

    assert first.profiles_created == 1
    assert second.contexts_unchanged == 1
    assert second.evaluations_unchanged == 1
    assert second.profiles_unchanged == 1
    assert db.query(MomentEvaluation).count() == 1
    assert db.query(CardRatingProfile).count() == 1


def test_falta_snapshot_exacto_falla_solo_ese_contexto(db, monkeypatch):
    _, valid = _seed_context(db)
    _, missing = _seed_context(db, mlb_id=111111, with_ratings=False)
    monkeypatch.setattr(
        "etl.services.walk_off_hr_pipeline.detect_walk_off_home_runs",
        lambda *_args, **_kwargs: _detection(valid.id, missing.id, created=2),
    )

    result = run_walk_off_hr_pipeline(db, object(), date_from=START, date_to=END)

    assert result.evaluated == 2
    assert result.profiles_created == 1
    assert result.failed == 1
    assert result.failures[0].moment_context_id == missing.id
    assert db.query(MomentEvaluation).count() == 2
    assert db.query(CardRatingProfile).count() == 1


def test_no_cuenta_candidato_no_confirmado_como_fallo(db, monkeypatch):
    failure = WalkOffHrDetectionFailure(
        824230, 41, 660271, "NO_CONFIRMADO", "UNCONFIRMED"
    )
    detection = WalkOffHrDetectionResult(
        selected=1,
        confirmed=0,
        created=0,
        updated=0,
        unchanged=0,
        unconfirmed=1,
        failed=0,
        moment_context_ids=(),
        failures=(failure,),
    )
    monkeypatch.setattr(
        "etl.services.walk_off_hr_pipeline.detect_walk_off_home_runs",
        lambda *_args, **_kwargs: detection,
    )

    result = run_walk_off_hr_pipeline(db, object(), date_from=START, date_to=END)
    assert (result.candidates, result.unconfirmed, result.failed) == (1, 1, 0)
