"""Hechos temporales comunes de Moment."""

import datetime as dt

import pytest

from app.models import MomentContext
from etl.services.moment_facts import moment_game_date


GAME_DATE = dt.date(2026, 8, 30)


def _context(facts):
    return MomentContext(facts=facts)


def test_fecha_canonica_desde_game():
    context = _context(
        {
            "game": {"game_date": GAME_DATE.isoformat()},
            "schedule_candidate": {"game_date": "2026-08-29"},
        }
    )

    assert moment_game_date(context) == GAME_DATE


def test_fecha_legacy_desde_schedule_candidate():
    context = _context(
        {"schedule_candidate": {"game_date": GAME_DATE.isoformat()}}
    )

    assert moment_game_date(context) == GAME_DATE


@pytest.mark.parametrize(
    "facts",
    ({}, {"game": {}}, {"game": {"game_date": None}}),
)
def test_rechaza_fecha_ausente(facts):
    with pytest.raises(ValueError, match="no contiene game_date factual"):
        moment_game_date(_context(facts))


def test_rechaza_fecha_iso_invalida():
    with pytest.raises(ValueError, match="game_date factual inválido"):
        moment_game_date(_context({"game": {"game_date": "30-08-2026"}}))
