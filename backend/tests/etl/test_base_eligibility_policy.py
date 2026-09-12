"""BaseEligibilityPolicy 1.1: la decisión es independiente y medible.

Cubre el contrato de base-eligibility-1.1: la frontera de minima evidencia de
publicacion (MINIMUM_BASE_EVIDENCE) es DISTINTA de la calibracion temporal de
base-evidence-1.0. BELOW_THRESHOLD no implica INELIGIBLE; solo falla cuando la
evidencia cae debajo del floor. ELIGIBLE se verifica por decision pura
(inyeccion) porque con base-evidence actual power/control/stuff siguen sin
calibrar.
"""

from decimal import Decimal

import pytest

from app.models import PlayerRatings
from etl.services.base_eligibility_policy import (
    BASE_ELIGIBILITY_POLICY_VERSION,
    ELIGIBLE,
    INELIGIBLE,
    INSUFFICIENT_EVIDENCE,
    MINIMUM_BASE_EVIDENCE,
    PROVISIONAL,
    assess_base_eligibility,
    decide_base_eligibility,
)
from etl.services.base_evidence_policy import (
    BASE_EVIDENCE_POLICY_VERSION,
    CALIBRATED_THRESHOLDS,
    AttributeEvidenceAssessment,
    BaseEvidenceAssessment,
)


def _ratings(
    *,
    role,
    contact=None,
    power=None,
    vision=None,
    clutch=None,
    velocity=None,
    control=None,
    movement=None,
    stuff=None,
    evidence=True,
):
    values = {
        "player_id": "p-1",
        "season": 2026,
        "role": role,
        "rating_model_version": "ratings-2.0",
        "distribution_version": "dist-1.0",
        "data_start_date": "2026-03-25",
        "data_end_date": "2026-09-02",
        "input_hash": "0" * 64,
    }
    if role == "BATTER":
        values.update(
            contact_rating=70,
            power_rating=70,
            vision_rating=70,
            clutch_rating=70,
            overall_rating=70,
            velocity_rating=None,
            control_rating=None,
            movement_rating=None,
            stuff_rating=None,
        )
        if evidence:
            values.update(
                contact_evidence=contact,
                power_evidence=power,
                vision_evidence=vision,
                clutch_evidence=clutch,
            )
    else:
        values.update(
            velocity_rating=80,
            control_rating=70,
            movement_rating=70,
            stuff_rating=70,
            overall_rating=75,
            contact_rating=None,
            power_rating=None,
            vision_rating=None,
            clutch_rating=None,
        )
        if evidence:
            values.update(
                velocity_evidence=velocity,
                control_evidence=control,
                movement_evidence=movement,
                stuff_evidence=stuff,
            )
    return PlayerRatings(**values)


def _attr(status, evidence=None, threshold=None):
    return AttributeEvidenceAssessment(
        status=status, evidence=evidence, threshold=threshold
    )


def _pure_evidence(attributes) -> BaseEvidenceAssessment:
    return BaseEvidenceAssessment(
        policy_version=BASE_EVIDENCE_POLICY_VERSION,
        attributes=attributes,
        eligibility="UNRESOLVED",
    )


def _pure_batter(contact=("PASS", Decimal("0.90000")),
                 power=("PASS", Decimal("0.95000")),
                 vision=("PASS", Decimal("0.90000")),
                 clutch=("NOT_APPLICABLE", None)):
    return _pure_evidence({
        "contact": _attr(contact[0], contact[1], CALIBRATED_THRESHOLDS["contact"]),
        "power": _attr(power[0], power[1]),
        "vision": _attr(vision[0], vision[1], CALIBRATED_THRESHOLDS["vision"]),
        "clutch": _attr(clutch[0], clutch[1]),
    })


def _pure_pitcher(velocity=("PASS", Decimal("0.50000")),
                  control=("PASS", Decimal("0.70000")),
                  movement=("PASS", Decimal("0.40000")),
                  stuff=("PASS", Decimal("0.80000"))):
    return _pure_evidence({
        "velocity": _attr(velocity[0], velocity[1], CALIBRATED_THRESHOLDS["velocity"]),
        "control": _attr(control[0], control[1]),
        "movement": _attr(movement[0], movement[1], CALIBRATED_THRESHOLDS["movement"]),
        "stuff": _attr(stuff[0], stuff[1]),
    })


# ---------------------------------------------------------------------------
# MINIMUM publication evidence: la frontera es el floor, no la calibracion
# ---------------------------------------------------------------------------


def test_floor_es_inclusivo_en_la_frontera(db=None):
    r = _ratings(role="BATTER", contact=Decimal("0.25"), power=0.92, vision=0.90, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.policy_version == BASE_ELIGIBILITY_POLICY_VERSION
    assert assessment.decision != INELIGIBLE
    assert assessment.decision == PROVISIONAL  # .25 es suficiente; BELOW .90 es señal


def test_floor_justo_debajo_es_ineligible(db=None):
    r = _ratings(role="BATTER", contact=Decimal("0.24999"), power=0.92, vision=0.90, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.decision == INELIGIBLE
    reason = assessment.reasons[0]
    assert reason["attribute"] == "contact"
    assert reason["assessment"] == "BELOW_THRESHOLD"
    assert reason["decision"] == INSUFFICIENT_EVIDENCE
    assert reason["minimum_evidence"] == "0.25"
    assert reason["calibrated_threshold"] == "0.90000"


def test_contact_080_es_provisional_no_ineligible(db=None):
    r = _ratings(role="BATTER", contact=Decimal("0.80"), power=0.92, vision=0.95, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.decision == PROVISIONAL
    assert assessment.decision != INELIGIBLE
    contact_reason = next(x for x in assessment.reasons if x["attribute"] == "contact")
    assert contact_reason["assessment"] == "BELOW_THRESHOLD"
    assert contact_reason["evidence"] == "0.80"


def test_velocity_030_es_provisional_aunque_umbral_sea_050(db=None):
    r = _ratings(
        role="PITCHER", velocity=Decimal("0.30"), control=0.80, movement=0.60, stuff=0.80
    )
    assessment = assess_base_eligibility(role="PITCHER", player_ratings=r)

    assert assessment.decision == PROVISIONAL
    velocity_reason = next(x for x in assessment.reasons if x["attribute"] == "velocity")
    assert velocity_reason["assessment"] == "BELOW_THRESHOLD"
    assert velocity_reason["calibrated_threshold"] == "0.50000"
    assert velocity_reason["minimum_evidence"] == "0.25"


def test_power_volatile_es_provisional(db=None):
    r = _ratings(role="BATTER", contact=0.95, power=0.92, vision=0.95, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.decision == PROVISIONAL
    assert {"attribute": "power", "assessment": "VOLATILE"} in assessment.reasons


def test_control_stuff_uncalibrated_es_provisional(db=None):
    r = _ratings(
        role="PITCHER", velocity=0.60, control=0.80, movement=0.60, stuff=0.80
    )
    assessment = assess_base_eligibility(role="PITCHER", player_ratings=r)

    assert assessment.decision == PROVISIONAL
    assert any(x["attribute"] == "control" and x["assessment"] == "UNCALIBRATED"
               for x in assessment.reasons)
    assert any(x["attribute"] == "stuff" and x["assessment"] == "UNCALIBRATED"
               for x in assessment.reasons)


def test_clutch_not_applicable_es_neutral(db=None):
    r = _ratings(role="BATTER", contact=0.95, power=0.92, vision=0.95, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.evidence.attributes["clutch"].status == "NOT_APPLICABLE"
    assert not any(x["attribute"] == "clutch" for x in assessment.reasons)


def test_floor_falla_gana_a_señal_volatile(db=None):
    r = _ratings(role="BATTER", contact=Decimal("0.15"), power=0.92, vision=0.95, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.decision == INELIGIBLE
    assert assessment.reasons[0]["attribute"] == "contact"
    assert assessment.reasons[0]["decision"] == INSUFFICIENT_EVIDENCE


def test_evidencia_null_es_ineligible_conservador(db=None):
    r = _ratings(role="BATTER", contact=None, power=None, vision=None, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.decision == INELIGIBLE
    reasons = {x["attribute"]: x for x in assessment.reasons}
    assert reasons["contact"]["evidence"] is None
    assert reasons["contact"]["decision"] == INSUFFICIENT_EVIDENCE
    assert reasons["vision"]["evidence"] is None


# ---------------------------------------------------------------------------
# ELIGIBLE: contrato verificable por decision pura (hoy inalcanzable via
# assess_base_evidence porque power/control/stuff siguen sin calibracion)
# ---------------------------------------------------------------------------


def test_todo_pass_y_not_applicable_es_eligible():
    evidence = _pure_batter()
    assessment = decide_base_eligibility(role="BATTER", evidence=evidence)

    assert assessment.decision == ELIGIBLE
    assert assessment.reasons == ()


def test_todo_pass_en_pitcher_es_eligible():
    assessment = decide_base_eligibility(role="PITCHER", evidence=_pure_pitcher())

    assert assessment.decision == ELIGIBLE
    assert assessment.reasons == ()


def test_below_threshold_puro_con_floor_suficiente_es_provisional():
    evidence = _pure_batter(contact=("BELOW_THRESHOLD", Decimal("0.80")))
    assessment = decide_base_eligibility(role="BATTER", evidence=evidence)

    assert assessment.decision == PROVISIONAL
    assert assessment.reasons[0]["attribute"] == "contact"


def test_todo_pass_pero_power_volatile_es_provisional():
    evidence = _pure_batter(power=("VOLATILE", Decimal("0.95000")))
    assessment = decide_base_eligibility(role="BATTER", evidence=evidence)

    assert assessment.decision == PROVISIONAL
    assert {"attribute": "power", "assessment": "VOLATILE"} in assessment.reasons


# ---------------------------------------------------------------------------
# integridad de config y API
# ---------------------------------------------------------------------------


def test_minimum_base_evidence_es_exactamente_los_atributos_calibrados():
    assert set(MINIMUM_BASE_EVIDENCE) == set(CALIBRATED_THRESHOLDS)


def test_role_desalineado_falla(db=None):
    r = _ratings(role="BATTER", contact=0.95, power=0.92, vision=0.95, clutch=None)

    with pytest.raises(ValueError):
        assess_base_eligibility(role="PITCHER", player_ratings=r)


def test_below_threshold_ya_no_es_ineligible_solo_por_status(db=None):
    """1.0 -> 1.1: el cambio semántico explícito que queremos conservar."""
    r = _ratings(role="BATTER", contact=Decimal("0.60"), power=0.92, vision=0.95, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.decision == PROVISIONAL  # v1 lo declaraba INELIGIBLE