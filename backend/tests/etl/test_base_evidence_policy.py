from decimal import Decimal
from types import SimpleNamespace

import pytest

from etl.services.base_evidence_policy import (
    BASE_EVIDENCE_POLICY_VERSION,
    assess_base_evidence,
)


def _ratings(role, **evidence):
    values = {
        "role": role,
        "contact_evidence": None,
        "power_evidence": None,
        "vision_evidence": None,
        "clutch_evidence": None,
        "velocity_evidence": None,
        "control_evidence": None,
        "movement_evidence": None,
        "stuff_evidence": None,
    }
    values.update(evidence)
    return SimpleNamespace(**values)


def test_batter_assessment_preserves_partial_calibration_semantics():
    result = assess_base_evidence(
        role="BATTER",
        player_ratings=_ratings(
            "BATTER",
            contact_evidence=Decimal("0.90000"),
            power_evidence=Decimal("0.95000"),
            vision_evidence=Decimal("0.89999"),
        ),
    )

    assert result.policy_version == BASE_EVIDENCE_POLICY_VERSION
    assert result.eligibility == "UNRESOLVED"
    assert result.attributes["contact"].status == "PASS"
    assert result.attributes["vision"].status == "BELOW_THRESHOLD"
    assert result.attributes["power"].status == "VOLATILE"
    assert result.attributes["clutch"].status == "NOT_APPLICABLE"


def test_pitcher_assessment_keeps_uncalibrated_attributes_unresolved():
    result = assess_base_evidence(
        role="PITCHER",
        player_ratings=_ratings(
            "PITCHER",
            velocity_evidence=Decimal("0.50000"),
            control_evidence=Decimal("0.99000"),
            movement_evidence=Decimal("0.39999"),
            stuff_evidence=Decimal("0.99000"),
        ),
    )

    assert result.attributes["velocity"].status == "PASS"
    assert result.attributes["movement"].status == "BELOW_THRESHOLD"
    assert result.attributes["control"].status == "UNCALIBRATED"
    assert result.attributes["stuff"].status == "UNCALIBRATED"


def test_rejects_role_mismatch():
    with pytest.raises(ValueError, match="does not match"):
        assess_base_evidence(role="PITCHER", player_ratings=_ratings("BATTER"))
