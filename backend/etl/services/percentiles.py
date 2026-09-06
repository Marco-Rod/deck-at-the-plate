"""Interpolación determinista para distribuciones y percentiles de habilidad."""

from collections.abc import Sequence


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
    ordered = sorted((float(x), float(rank)) for x, rank in points)
    if value <= ordered[0][0]:
        statistical = ordered[0][1]
    elif value >= ordered[-1][0]:
        statistical = ordered[-1][1]
    else:
        statistical = 0.0
        for (left, left_rank), (right, right_rank) in zip(ordered, ordered[1:]):
            if left <= value <= right:
                if right == left:
                    statistical = (left_rank + right_rank) / 2
                else:
                    statistical = left_rank + (value - left) / (right - left) * (right_rank - left_rank)
                break
    statistical = min(1.0, max(0.0, statistical))
    return statistical if direction == "higher" else 1.0 - statistical
