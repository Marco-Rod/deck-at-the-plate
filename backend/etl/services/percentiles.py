"""Interpolación determinista para distribuciones y percentiles de habilidad."""

from collections.abc import Sequence
from itertools import groupby


def percentile(values: Sequence[float], quantile: float) -> float:
    """Percentil lineal usando la posición ``(n - 1) * quantile``."""
    if not values:
        raise ValueError("percentile requiere al menos un valor")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile debe estar entre 0 y 1")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def percentile_rank(value: float, points: Sequence[tuple[float, float]], direction: str = "higher") -> float:
    """Interpola el rango de un valor entre puntos ``(valor, percentil)``."""
    if not points:
        raise ValueError("percentile_rank requiere puntos")
    if direction not in {"higher", "lower"}:
        raise ValueError("direction debe ser higher o lower")
    raw_points = sorted((float(x), float(rank)) for x, rank in points)
    # Una métrica discreta puede ocupar varios percentiles con el mismo valor.
    # Ese empate se representa por el centro del rango que ocupa, no por su
    # primera ancla (lo que convertiría, por ejemplo, HBP%=0 en P100 inverso).
    ordered = []
    for point_value, tied in groupby(raw_points, key=lambda point: point[0]):
        ranks = [rank for _, rank in tied]
        ordered.append((point_value, (min(ranks) + max(ranks)) / 2))
    if value <= ordered[0][0]:
        statistical = ordered[0][1]
    elif value >= ordered[-1][0]:
        statistical = ordered[-1][1]
    else:
        statistical = 0.0
        for (left, left_rank), (right, right_rank) in zip(ordered, ordered[1:]):
            if left <= value <= right:
                statistical = left_rank + (value - left) / (right - left) * (right_rank - left_rank)
                break
    statistical = min(1.0, max(0.0, statistical))
    return statistical if direction == "higher" else 1.0 - statistical


def distribution_points(distribution) -> list[tuple[float, float]]:
    """Construye todos los anclajes, incluidos extremos P00 y P100."""
    return [
        (float(distribution.minimum), 0.00),
        (float(distribution.p05), 0.05),
        (float(distribution.p10), 0.10),
        (float(distribution.p25), 0.25),
        (float(distribution.p50), 0.50),
        (float(distribution.p75), 0.75),
        (float(distribution.p90), 0.90),
        (float(distribution.p95), 0.95),
        (float(distribution.maximum), 1.00),
    ]


def distribution_percentile_rank(value: float, distribution, direction: str = "higher") -> float:
    return percentile_rank(value, distribution_points(distribution), direction)


def percentile_rating(percentile_value: float) -> int:
    """Convierte P00..P100 a la escala inclusiva 40..99."""
    bounded = min(1.0, max(0.0, float(percentile_value)))
    return round(40 + bounded * 59)
