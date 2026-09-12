from decimal import Decimal
from types import SimpleNamespace as S

import pytest

from etl.services.rating_evidence import component_evidence, movement_evidence, quantize_evidence


def test_composite_uses_effective_weights_and_rounds_only_at_end():
    result = S(rating=80, components=[
        S(component_weight=.45, shrinkage_weight=.2),
        S(component_weight=.30, shrinkage_weight=.8),
    ])
    assert component_evidence(result) == Decimal("0.44000")


def test_movement_normalizes_evaluable_usage():
    result = S(rating=80, evaluable_usage=.6, pitches=[
        S(usage=.4, shrinkage_weight=.5), S(usage=.2, shrinkage_weight=.25),
    ])
    assert movement_evidence(result) == Decimal("0.41667")


def test_precision_boundaries_and_missing():
    assert quantize_evidence(1 / 11) == Decimal("0.09091")
    assert quantize_evidence(0) == Decimal("0.00000")
    assert quantize_evidence(1) == Decimal("1.00000")
    assert quantize_evidence(None) is None
    assert component_evidence(S(rating=None, components=[])) is None


@pytest.mark.parametrize("value", [-.01, 1.01, float("nan"), float("inf")])
def test_invalid_evidence_is_rejected(value):
    with pytest.raises(ValueError):
        quantize_evidence(value)
