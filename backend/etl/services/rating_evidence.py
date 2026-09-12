"""Observed-data weights, not calibrated probabilities of correctness.

Derived properties deliberately stay outside dataclass fields: adding evidence
must not change the existing statistical input hashes.
"""

from decimal import Decimal, ROUND_HALF_UP
from math import isfinite


def quantize_evidence(value):
    if value is None:
        return None
    if not isfinite(float(value)) or not 0 <= value <= 1:
        raise ValueError("evidence must be finite and within 0..1")
    return Decimal(str(value)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)


def component_evidence(result):
    components = getattr(result, "components", ())
    if result.rating is None or not components:
        return None
    coverage = sum(c.component_weight for c in components)
    if coverage <= 0:
        return None
    return quantize_evidence(sum(
        c.component_weight * c.shrinkage_weight / coverage for c in components
    ))


def movement_evidence(result):
    pitches = getattr(result, "pitches", ())
    if result.rating is None or not pitches or result.evaluable_usage <= 0:
        return None
    return quantize_evidence(sum(
        p.usage * p.shrinkage_weight / result.evaluable_usage for p in pitches
    ))
