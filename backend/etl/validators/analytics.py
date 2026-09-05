"""Validación post-agregación de perfiles analytics (spec secciones 35-41 y 48).

Reglas centrales (mismas que los CHECK de la DB, verificadas antes del flush):
    - Toda tasa es 0..1 (o None cuando no hay denominador).
    - Los conteos son enteros >= 0.
    - sample_size debe poder compararse contra su campo canónico.
"""

from typing import Any, Mapping, Optional


def _bool_to_error(errors: list[str], ok: bool, message: str) -> None:
    if not ok:
        errors.append(message)


def validate_rate(errors: list[str], name: str, value: Optional[Any]) -> None:
    if value is None:
        return
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        _bool_to_error(errors, False, f"{name} no es numérico: {value!r}")
        return
    _bool_to_error(errors, 0.0 <= numeric <= 1.0, f"{name} fuera de rango 0..1: {value!r}")


def validate_non_negative(errors: list[str], name: str, value: Optional[Any]) -> None:
    if value is None:
        return
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        _bool_to_error(errors, False, f"{name} no es entero: {value!r}")
        return
    _bool_to_error(errors, numeric >= 0, f"{name} negativo: {numeric}")


def validate_proportional_denominator(
    errors: list[str],
    *,
    sample_size: int,
    label: str,
    denominator_expected: int,
) -> None:
    """sample_size debe coincidir con el denominador canónico del perfil (V1)."""
    _bool_to_error(
        errors,
        sample_size == denominator_expected,
        f"sample_size={sample_size} != {label}={denominator_expected}",
    )


def validate_profile(
    profile: Mapping[str, Any],
    *,
    rate_fields: tuple[str, ...],
    non_negative_fields: tuple[str, ...],
    sample_field: Optional[str] = None,
    denominator_field: Optional[str] = None,
) -> list[str]:
    """Devuelve lista de errores de un perfil agregado; vacía si es válido."""
    errors: list[str] = []
    for field in rate_fields:
        validate_rate(errors, field, profile.get(field))
    for field in non_negative_fields:
        validate_non_negative(errors, field, profile.get(field))
    if sample_field and denominator_field:
        sample = profile.get(sample_field)
        denominator = profile.get(denominator_field)
        if sample is not None and denominator is not None:
            validate_proportional_denominator(
                errors, sample_size=int(sample), label=denominator_field, denominator_expected=int(denominator)
            )
    return errors