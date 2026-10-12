"""Gates de jugabilidad para un catálogo de cartas.

Estas reglas sólo inspeccionan cartas ya materializadas. No conocen SQLAlchemy
ni el lifecycle del catálogo; por eso pueden probarse con objetos mínimos y el
servicio de catálogo se limita a reunir los datos que necesitan.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from app.core.enums import PITCHER_POSITIONS
from app.core.enums import PitchType
from app.engine.starter_pack import REQUIRED_POSITIONS, TOTAL_CARDS, select_starter_cards


@dataclass
class ValidationResult:
    ok: bool
    detail: list[str] = field(default_factory=list)


def _is_pitcher(card: object) -> bool:
    return (
        getattr(card, "position", None) in PITCHER_POSITIONS
        or bool(getattr(card, "is_two_way", False))
    )


def _is_batter(card: object) -> bool:
    return not _is_pitcher(card) or bool(getattr(card, "is_two_way", False))


def validate_cpu_roster_coverage(
    cards: Sequence[object],
    team_ids: Iterable[str],
    *,
    minimum_batters: int = 9,
    minimum_pitchers: int = 2,
) -> ValidationResult:
    """Comprueba que cada franquicia mapeada pueda iniciar un juego CPU."""
    mapped_teams = tuple(dict.fromkeys(team_ids))
    by_team: dict[str, list[object]] = {team_id: [] for team_id in mapped_teams}
    for card in cards:
        team_cards = by_team.get(getattr(card, "team_id", None))
        if team_cards is not None:
            team_cards.append(card)

    missing: list[str] = []
    detail = [f"franquicias mapeadas={len(mapped_teams)}"]
    for team_id in mapped_teams:
        team_cards = by_team[team_id]
        batters = sum(1 for card in team_cards if _is_batter(card))
        pitchers = sum(1 for card in team_cards if _is_pitcher(card))
        if batters < minimum_batters or pitchers < minimum_pitchers:
            missing.append(
                f"{team_id}: bateadores={batters}/{minimum_batters}, "
                f"pitchers={pitchers}/{minimum_pitchers}"
            )
    detail.append(f"rosters incompletos={len(missing)}")
    detail.extend(missing)
    return ValidationResult(ok=not missing, detail=detail)


def validate_starter_pack_coverage(
    cards: Sequence[object], team_ids: Iterable[str]
) -> ValidationResult:
    """Ejecuta el selector real para cada franquicia elegible.

    Usar el selector evita que el gate apruebe un pool que parece suficiente
    por conteos, pero que el onboarding no puede convertir en un starter pack.
    El RNG fijo hace el diagnóstico reproducible.
    """
    mapped_teams = tuple(dict.fromkeys(team_ids))
    issues: list[str] = []
    for team_id in mapped_teams:
        team_cards = [card for card in cards if getattr(card, "team_id", None) == team_id]
        other_cards = [card for card in cards if getattr(card, "team_id", None) != team_id]
        selected = select_starter_cards(team_cards, other_cards, rng=random.Random(0))
        selected_ids = [getattr(card, "id", None) for card in selected]
        covered = {getattr(card, "position", None) for card in selected}
        missing_positions = sorted(set(REQUIRED_POSITIONS) - covered)
        has_pitcher = any(_is_pitcher(card) for card in selected)
        if (
            len(selected) != TOTAL_CARDS
            or len(selected_ids) != len(set(selected_ids))
            or not has_pitcher
            or missing_positions
        ):
            issues.append(
                f"{team_id}: starter={len(selected)}/{TOTAL_CARDS}, "
                f"pitcher={'sí' if has_pitcher else 'no'}, "
                f"posiciones faltantes={','.join(missing_positions) or 'ninguna'}"
            )
    detail = [f"starter packs evaluados={len(mapped_teams)}", f"starter packs inválidos={len(issues)}"]
    detail.extend(issues)
    return ValidationResult(ok=not issues, detail=detail)


def validate_pitcher_repertoires(cards: Sequence[object]) -> ValidationResult:
    """Cada pitcher debe exponer al motor al menos un pitcheo soportado."""
    supported = {pitch.value for pitch in PitchType if pitch is not PitchType.IBB}
    invalid: list[str] = []
    pitchers = [card for card in cards if _is_pitcher(card)]
    for card in pitchers:
        repertoire = getattr(card, "repertoire", None) or []
        types = [entry.get("pitch_type") for entry in repertoire if isinstance(entry, dict)]
        if not types or any(pitch_type not in supported for pitch_type in types):
            invalid.append(f"{getattr(card, 'id', '?')}: repertorio inválido")
    return ValidationResult(
        ok=not invalid,
        detail=[f"pitchers evaluados={len(pitchers)}", f"repertorios inválidos={len(invalid)}", *invalid],
    )
