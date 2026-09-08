"""Evaluación versionada de WALK_OFF_HR sin producir ratings ni ajustes."""

import datetime as dt
from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    MomentEvaluation,
    MomentType,
    MomentContextSourceType,
    Player,
)
from etl.services.moment_contexts import persist_moment_context
from etl.services.moment_evaluations import (
    MULTI_HR_GAME_RULES,
    WALK_OFF_HR_RULES,
    evaluate_moment,
)


OCCURRED_AT = dt.datetime(2026, 9, 5, 21, 15, tzinfo=dt.timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _context(db, *, role="BATTER", batting=None):
    player = Player(mlb_id=660271, full_name="Shohei Ohtani")
    edition = CardEdition(
        code="2026_WALK_OFF_001",
        name="Walk-Off Hero",
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference="mlb-game:824230",
        metadata_payload={},
    )
    db.add_all([player, edition])
    db.commit()
    facts = (
        {
            "game": {"game_pk": 824230},
            "batting": batting
            or {
                "plate_appearances": 5,
                "hits": 4,
                "home_runs": 2,
                "runs_batted_in": 5,
                "walk_off": True,
            },
        }
        if role == "BATTER"
        else {
            "game": {"game_pk": 824230},
            "pitching": {"pitches": 101, "strikeouts": 12},
        }
    )
    result = persist_moment_context(
        db,
        player_id=player.id,
        card_edition_id=edition.id,
        role=role,
        occurred_at=OCCURRED_AT,
        source_type=MomentContextSourceType.STATCAST,
        source_reference="statcast:824230:660271",
        facts=facts,
    )
    return result.moment_context_id, player, edition


def _multi_context(db, *, mlb_id, batting, home_runs):
    player = Player(mlb_id=mlb_id, full_name=f"Player {mlb_id}")
    edition = CardEdition(
        code=f"2026_MULTI_HR_{mlb_id}",
        name="Multi-Home Run Game",
        edition_type=CardEditionType.MOMENT,
        season=2026,
        version="edition-1.0",
        source_type=CardEditionSourceType.GAME,
        source_reference=f"mlb-game:900001:batter:{mlb_id}",
        metadata_payload={},
    )
    db.add_all([player, edition])
    db.commit()
    result = persist_moment_context(
        db,
        player_id=player.id,
        card_edition_id=edition.id,
        role="BATTER",
        occurred_at=OCCURRED_AT,
        source_type=MomentContextSourceType.MLB_STATS_API,
        source_reference=f"mlb-stats-api:game/900001:batter/{mlb_id}",
        facts={
            "game": {"game_pk": 900001, "inning_count": 9},
            "batting": {
                "plate_appearances": 5,
                "at_bats": 4,
                **batting,
            },
            "home_runs": home_runs,
        },
    )
    return result.moment_context_id


def _hr(inning, half, pre_home, pre_away, post_home, post_away):
    return {
        "inning": inning,
        "half_inning": half,
        "at_bat_index": inning * 10,
        "occurred_at": OCCURRED_AT.isoformat(),
        "runs_batted_in": 1,
        "pre_home_score": pre_home,
        "pre_away_score": pre_away,
        "post_home_score": post_home,
        "post_away_score": post_away,
    }


def test_evalua_walk_off_hr_con_scores_reproducibles(db):
    context_id, _, _ = _context(db)

    result = evaluate_moment(db, moment_context_id=context_id)
    evaluation = db.get(MomentEvaluation, result.moment_evaluation_id)

    assert result.status == "CREATED"
    assert result.moment_type == MomentType.WALK_OFF_HR
    assert result.performance_score == Decimal("0.84000")
    assert result.leverage_score == Decimal("1.00000")
    assert result.statistical_uncommonness == Decimal("0.88000")
    assert result.significance_score == Decimal("0.92000")
    assert result.evaluation_version == "moment-eval-1.0"
    assert evaluation.rules_payload["significance_leverage_weight"] == "0.45"
    assert len(result.input_hash) == 64


def test_misma_evaluacion_es_unchanged(db):
    context_id, _, _ = _context(db)
    created = evaluate_moment(db, moment_context_id=context_id)
    unchanged = evaluate_moment(db, moment_context_id=context_id)

    assert unchanged.status == "UNCHANGED"
    assert unchanged.moment_evaluation_id == created.moment_evaluation_id
    assert unchanged.input_hash == created.input_hash
    assert db.query(MomentEvaluation).count() == 1


def test_evalua_multi_hr_game_con_performance_y_uncommonness_versionados(db):
    context_id = _multi_context(
        db,
        mlb_id=100,
        batting={"hits": 2, "home_runs": 2, "runs_batted_in": 2},
        home_runs=[
            _hr(2, "Bottom", 0, 0, 1, 0),
            _hr(6, "Bottom", 7, 1, 9, 1),
        ],
    )

    result = evaluate_moment(db, moment_context_id=context_id)

    assert result.status == "CREATED"
    assert result.moment_type == MomentType.MULTI_HR_GAME
    assert result.performance_score == Decimal("0.62000")
    assert result.statistical_uncommonness == Decimal("0.72000")
    assert result.leverage_score == Decimal("0.30000")
    assert result.significance_score == Decimal("0.59100")
    assert result.evaluation_version == "moment-eval-1.0"


def test_tres_hr_superan_claramente_un_juego_de_dos_hr(db):
    two_hr_id = _multi_context(
        db,
        mlb_id=101,
        batting={"hits": 2, "home_runs": 2, "runs_batted_in": 2},
        home_runs=[
            _hr(2, "Top", 0, 0, 0, 1),
            _hr(5, "Top", 1, 1, 1, 2),
        ],
    )
    three_hr_id = _multi_context(
        db,
        mlb_id=102,
        batting={"hits": 4, "home_runs": 3, "runs_batted_in": 6},
        home_runs=[
            _hr(2, "Top", 0, 0, 0, 1),
            _hr(5, "Top", 1, 1, 1, 2),
            _hr(8, "Top", 2, 2, 2, 3),
        ],
    )

    two_hr = evaluate_moment(db, moment_context_id=two_hr_id)
    three_hr = evaluate_moment(db, moment_context_id=three_hr_id)

    assert three_hr.performance_score == Decimal("0.91500")
    assert three_hr.statistical_uncommonness == Decimal("0.93000")
    assert three_hr.significance_score > two_hr.significance_score


def test_empate_tardio_tiene_mas_leverage_que_dos_hr_en_paliza(db):
    yainer_id = _multi_context(
        db,
        mlb_id=103,
        batting={"hits": 2, "home_runs": 2, "runs_batted_in": 2},
        home_runs=[
            _hr(2, "Bottom", 0, 0, 1, 0),
            _hr(8, "Top", 6, 5, 6, 6),
        ],
    )
    wells_id = _multi_context(
        db,
        mlb_id=104,
        batting={"hits": 2, "home_runs": 2, "runs_batted_in": 4},
        home_runs=[
            _hr(3, "Bottom", 7, 1, 9, 1),
            _hr(8, "Bottom", 14, 1, 16, 1),
        ],
    )

    yainer = evaluate_moment(db, moment_context_id=yainer_id)
    wells = evaluate_moment(db, moment_context_id=wells_id)

    assert yainer.leverage_score == Decimal("0.65000")
    assert wells.leverage_score == Decimal("0.02500")
    assert yainer.leverage_score > wells.leverage_score


def test_multi_hr_rerun_es_unchanged(db):
    context_id = _multi_context(
        db,
        mlb_id=105,
        batting={"hits": 3, "home_runs": 2, "runs_batted_in": 3},
        home_runs=[
            _hr(2, "Top", 0, 0, 0, 1),
            _hr(7, "Top", 1, 1, 1, 2),
        ],
    )
    created = evaluate_moment(db, moment_context_id=context_id)
    unchanged = evaluate_moment(db, moment_context_id=context_id)

    assert unchanged.status == "UNCHANGED"
    assert unchanged.moment_evaluation_id == created.moment_evaluation_id
    assert db.query(MomentEvaluation).count() == 1


def test_cambio_de_hechos_actualiza_misma_version(db):
    context_id, player, edition = _context(db)
    created = evaluate_moment(db, moment_context_id=context_id)
    corrected = persist_moment_context(
        db,
        player_id=player.id,
        card_edition_id=edition.id,
        role="BATTER",
        occurred_at=OCCURRED_AT,
        source_type=MomentContextSourceType.STATCAST,
        source_reference="statcast:824230:660271",
        facts={
            "game": {"game_pk": 824230},
            "batting": {
                "plate_appearances": 5,
                "hits": 4,
                "home_runs": 2,
                "runs_batted_in": 6,
                "walk_off": True,
            },
        },
    )
    assert corrected.status == "UPDATED"

    updated = evaluate_moment(db, moment_context_id=context_id)
    assert updated.status == "UPDATED"
    assert updated.moment_evaluation_id == created.moment_evaluation_id
    assert updated.input_hash != created.input_hash
    assert updated.performance_score == Decimal("0.85000")


def test_versiones_de_evaluador_coexisten(db):
    context_id, _, _ = _context(db)
    first = evaluate_moment(db, moment_context_id=context_id)
    v2_rules = replace(
        WALK_OFF_HR_RULES,
        evaluation_version="moment-eval-2.0",
        uncommonness_extra_home_run=Decimal("0.10"),
    )
    second = evaluate_moment(db, moment_context_id=context_id, rules=v2_rules)

    assert first.moment_evaluation_id != second.moment_evaluation_id
    assert second.evaluation_version == "moment-eval-2.0"
    assert db.query(MomentEvaluation).count() == 2


def test_rechaza_reglas_con_pesos_no_normalizados(db):
    context_id, _, _ = _context(db)
    invalid_rules = replace(
        WALK_OFF_HR_RULES,
        significance_leverage_weight=Decimal("0.50"),
    )
    with pytest.raises(ValueError, match="sumar 1"):
        evaluate_moment(db, moment_context_id=context_id, rules=invalid_rules)


@pytest.mark.parametrize(
    "batting",
    [
        {
            "hits": 4,
            "home_runs": 2,
            "runs_batted_in": 5,
            "walk_off": False,
        },
        {
            "hits": 4,
            "home_runs": 0,
            "runs_batted_in": 5,
            "walk_off": True,
        },
    ],
)
def test_no_persiste_contextos_que_no_son_walk_off_hr(db, batting):
    context_id, _, _ = _context(db, batting=batting)
    result = evaluate_moment(db, moment_context_id=context_id)

    assert result.status == "SKIPPED_UNSUPPORTED"
    assert result.moment_evaluation_id is None
    assert db.query(MomentEvaluation).count() == 0


def test_pitcher_queda_preparado_para_futuras_familias_sin_falsa_evaluacion(db):
    context_id, _, _ = _context(db, role="PITCHER")
    result = evaluate_moment(db, moment_context_id=context_id)
    assert result.status == "SKIPPED_UNSUPPORTED"
    assert db.query(MomentEvaluation).count() == 0


def test_constraints_rechazan_scores_fuera_de_rango(db):
    context_id, _, _ = _context(db)
    db.add(
        MomentEvaluation(
            moment_context_id=context_id,
            moment_type=MomentType.WALK_OFF_HR,
            significance_score=Decimal("1.01"),
            performance_score=Decimal("0.84"),
            leverage_score=Decimal("1.00"),
            statistical_uncommonness=Decimal("0.88"),
            evaluation_version="invalid",
            rules_payload={},
            input_hash="x" * 64,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_modelo_no_contiene_ajustes_ratings_ni_rarity():
    columns = set(MomentEvaluation.__table__.columns.keys())
    assert "rating_adjustments" not in columns
    assert "ratings" not in columns
    assert "rarity" not in columns
