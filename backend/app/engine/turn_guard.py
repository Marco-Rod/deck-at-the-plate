from fastapi import HTTPException, status
from app.models import GameSession

def verify_player_turn(game: GameSession, user_id: str, required_role: str) -> None:
    """
    Entrada Alta (is_top_inning = True): Batea Visitante (away), Lanzador Local (home).
    Entrada Baja (is_top_inning = False): Batea Local (home), Lanzador Visitante (away).
    """
    if required_role.upper() == "PITCHER":
        expected_user_id = game.home_user_id if game.is_top_inning else game.away_user_id
    elif required_role.upper() == "BATTER":
        expected_user_id = game.away_user_id if game.is_top_inning else game.home_user_id
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol de juego no válido.")

    if user_id != expected_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No es tu turno de actuar. Se esperaba la acción del usuario con rol {required_role}."
        )