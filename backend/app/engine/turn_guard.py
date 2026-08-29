"""
Guardia de turno (lógica pura)
===============================
Determina si un usuario tiene el turno activo bajo un rol (PITCHER/BATTER) en
la media entrada actual (TOP/BOT).

Este módulo NO depende de FastAPI: expone decisiones puras. La traducción a
HTTP (HTTPException 400/403) queda en el router que lo consume.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import GameSession


def expected_actor(game: "GameSession", required_role: str):
    """
    Retorna el ``user_id`` al que le corresponde actuar según el rol y la media
    entrada. Retorna ``None`` si el rol no es válido.

    - PITCHER: lanza el local (HOME) en la Alta, el visitante (AWAY) en la Baja.
    - BATTER:  batea el visitante (AWAY) en la Alta, el local (HOME) en la Baja.
    """
    normalized = required_role.upper()
    if normalized == "PITCHER":
        return game.home_user_id if game.is_top_inning else game.away_user_id
    if normalized == "BATTER":
        return game.away_user_id if game.is_top_inning else game.home_user_id
    return None


def is_player_turn(game: "GameSession", user_id: str, required_role: str) -> bool:
    """
    Decide si ``user_id`` tiene el turno activo para ``required_role``.
    La CPU (``CPU_BOT``) se considera "en turno" automáticamente cuando le
    corresponde actuar (bypass del control humano).
    """
    expected = expected_actor(game, required_role)
    if expected is None:
        return False
    if expected == "CPU_BOT":
        return True
    return user_id == expected