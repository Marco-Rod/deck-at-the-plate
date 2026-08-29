"""
Repositorio de sesiones de juego (GameSession)
===============================================
Centraliza las consultas de lectura/escritura de partidas.
"""
from app.models import GameSession  # noqa: F401  (re-export para tipo)


def get_game_by_id(db, game_id) -> "GameSession | None":
    """
    Retorna la sesión de juego con el id dado, o None si no existe.
    """
    return db.query(GameSession).filter(GameSession.id == game_id).first()