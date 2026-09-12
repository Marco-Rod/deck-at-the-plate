"""BaseEligibilityPolicy: la decisión es independiente y medible."""

import pytest

from app.models import PlayerRatings
from etl.services.base_eligibility_policy import (
    BASE_ELIGIBILITY_POLICY_VERSION,
    ELIGIBLE,
    INELIGIBLE,
    PROVISIONAL,
    assess_base_eligibility,
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


def test_batter_contact_bajo_es_ineligible(db=None):
    r = _ratings(role="BATTER", contact=0.60, power=0.90, vision=0.95, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.policy_version == BASE_ELIGIBILITY_POLICY_VERSION
    assert assessment.decision == INELIGIBLE
    assert "contact" in assessment.reasons[0]


def test_pitcher_velocity_bajo_es_ineligible(db=None):
    r = _ratings(
        role="PITCHER", velocity=0.30, control=0.80, movement=0.60, stuff=0.80
    )
    assessment = assess_base_eligibility(role="PITCHER", player_ratings=r)

    assert assessment.decision == INELIGIBLE
    assert "velocity" in assessment.reasons[0]


def test_batter_calibrado_pasa_y_quedan_señales_provisionales(db=None):
    r = _ratings(role="BATTER", contact=0.95, power=0.92, vision=0.95, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.decision == PROVISIONAL
    assert any("power" in reason for reason in assessment.reasons)
    assert not any("clutch" in reason for reason in assessment.reasons)


def test_pitcher_calibrado_pasa_y_quedan_señales_provisionales(db=None):
    r = _ratings(
        role="PITCHER", velocity=0.60, control=0.80, movement=0.50, stuff=0.80
    )
    assessment = assess_base_eligibility(role="PITCHER", player_ratings=r)

    assert assessment.decision == PROVISIONAL
    assert any("control" in reason for reason in assessment.reasons)
    assert any("stuff" in reason for reason in assessment.reasons)


def test_evidencia_null_quiere_decir_below_threshold(db=None):
    r = _ratings(role="BATTER", contact=None, power=None, vision=None, clutch=None)
    assessment = assess_base_eligibility(role="BATTER", player_ratings=r)

    assert assessment.decision == INELIGIBLE
    assert "contact" in assessment.reasons[0] and "vision" in assessment.reasons[0]


def test_role_desalineado_falla(db=None):
    r = _ratings(role="BATTER", contact=0.95, power=0.92, vision=0.95, clutch=None)

    with pytest.raises(ValueError):
        assess_base_eligibility(role="PITCHER", player_ratings=r)