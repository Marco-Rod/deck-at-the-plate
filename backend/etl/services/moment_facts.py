"""Lectura validada de hechos comunes a todas las familias de Moment."""

from datetime import date

from app.models import MomentContext


def moment_game_date(context: MomentContext) -> date:
    """Obtiene la fecha factual del juego desde el formato actual o legacy."""
    facts = context.facts
    if not isinstance(facts, dict):
        raise ValueError("MomentContext no contiene facts válidos")
    game = facts.get("game")
    schedule_candidate = facts.get("schedule_candidate")
    raw_value = (
        game.get("game_date") if isinstance(game, dict) else None
    ) or (
        schedule_candidate.get("game_date")
        if isinstance(schedule_candidate, dict)
        else None
    )
    if not isinstance(raw_value, str):
        raise ValueError("MomentContext no contiene game_date factual")
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError("MomentContext contiene game_date factual inválido") from exc
