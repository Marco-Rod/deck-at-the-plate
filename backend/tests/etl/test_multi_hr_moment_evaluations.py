"""Evaluación batch de los MULTI_HR_GAME descubiertos."""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    MomentContext,
    MomentContextSourceType,
    MomentEvaluation,
    MomentType,
    Player,
)
from etl.cli import _build_parser
from etl.services.moment_contexts import persist_moment_context
from etl.services.multi_hr_moment_evaluations import (
    evaluate_discovered_multi_hr_moments,
)


OCCURRED_AT = dt.datetime(2026, 8, 30, 22, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _context(db, mlb_id, *, multi_hr=True, occurred_at=OCCURRED_AT):
    player = Player(mlb_id=mlb_id, full_name=f"Player {mlb_id}")
    edition = CardEdition(
        code=f"2026_MOMENT_{mlb_id}",
        name="Moment",
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference=f"mlb-game:900001:batter:{mlb_id}",
        metadata_payload={},
    )
    db.add_all([player, edition])
    db.commit()
    batting = {
        "plate_appearances": 5,
        "at_bats": 4,
        "hits": 3,
        "home_runs": 2,
        "runs_batted_in": 3,
    }
    facts = {"game": {"game_pk": 900001}, "batting": batting}
    if multi_hr:
        facts["home_runs"] = [
            {
                "inning": inning,
                "half_inning": "Top",
                "at_bat_index": inning * 10,
                "pre_home_score": 0,
                "pre_away_score": index,
                "post_home_score": 0,
                "post_away_score": index + 1,
            }
            for index, inning in enumerate((2, 7))
        ]
    else:
        batting["walk_off"] = True
    return persist_moment_context(
        db,
        player_id=player.id,
        card_edition_id=edition.id,
        role="BATTER",
        occurred_at=occurred_at,
        source_type=MomentContextSourceType.MLB_STATS_API,
        source_reference=f"mlb-stats-api:game/900001:batter/{mlb_id}",
        facts=facts,
    ).moment_context_id


def test_evalua_solo_multi_hr_y_es_idempotente(db):
    _context(db, 100)
    _context(db, 200)
    _context(db, 300, multi_hr=False)

    first = evaluate_discovered_multi_hr_moments(db)
    second = evaluate_discovered_multi_hr_moments(db)

    assert (first.selected, first.created, first.failed) == (2, 2, 0)
    assert (second.selected, second.unchanged, second.failed) == (2, 2, 0)
    assert first.moment_evaluation_ids == second.moment_evaluation_ids
    assert db.query(MomentEvaluation).count() == 2
    assert {
        evaluation.moment_type for evaluation in db.query(MomentEvaluation).all()
    } == {MomentType.MULTI_HR_GAME}


def test_dos_exitos_sobreviven_al_fallo_del_tercer_contexto(db, monkeypatch):
    _context(db, 100, occurred_at=OCCURRED_AT - dt.timedelta(hours=2))
    _context(db, 200, occurred_at=OCCURRED_AT - dt.timedelta(hours=1))
    failing_id = _context(db, 300, occurred_at=OCCURRED_AT)
    from etl.services import multi_hr_moment_evaluations as service

    real_evaluate = service.evaluate_moment

    def evaluate(db, *, moment_context_id, commit=True):
        if moment_context_id == failing_id:
            raise RuntimeError("broken context")
        return real_evaluate(
            db, moment_context_id=moment_context_id, commit=commit
        )

    monkeypatch.setattr(service, "evaluate_moment", evaluate)
    first = evaluate_discovered_multi_hr_moments(db)
    second = evaluate_discovered_multi_hr_moments(db)

    assert (first.selected, first.created, first.failed) == (3, 2, 1)
    assert (second.selected, second.unchanged, second.failed) == (3, 2, 1)
    assert first.failures[0].moment_context_id == failing_id
    assert second.failures[0].moment_context_id == failing_id
    assert db.query(MomentEvaluation).count() == 2


def test_cli_expone_batch_sin_parametros_de_ratings():
    args = _build_parser().parse_args(["evaluate-multi-hr-moments"])
    assert args.command == "evaluate-multi-hr-moments"
