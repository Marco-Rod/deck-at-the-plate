"""Operaciones numéricas compartidas por las metodologías de ratings."""

from decimal import Decimal, ROUND_HALF_UP


def round_rating(value: float | Decimal) -> int:
    """Redondea composites .5 hacia arriba de forma explícita y estable."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
