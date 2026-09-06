"""Normalizaciones misceláneas de valores (spec sección 12).

Pequeñas transformaciones de formato que deben ser consistentes en todo el
pipeline (inning like, códigos limpios, counts).
"""

from typing import Optional


def clean_code(value: Optional[str]) -> Optional[str]:
    """trim + uppercase, ''/None → None."""
    if value is None:
        return None
    cleaned = value.strip().upper()
    return cleaned or None


def normalize_inning_topbot(value: Optional[str]) -> Optional[str]:
    """'Top'/'T' → 'Top'; 'Bottom'/'B'/'Bot' → 'Bottom'; otro → None."""
    if value is None:
        return None
    cleaned = value.strip().lower()
    if cleaned in {"top", "t"}:
        return "Top"
    if cleaned in {"bottom", "bot", "b"}:
        return "Bottom"
    return None


def clamp_count(value: Optional[int], lower: int, upper: int) -> Optional[int]:
    """Devuelve el int dentro de [lower, upper] o None si no computa."""
    if value is None:
        return None
    return max(lower, min(upper, int(value)))
