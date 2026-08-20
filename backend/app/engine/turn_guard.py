from fastapi import HTTPException, status
from app.models import GameSession

def verify_player_turn(game: GameSession, user_id: str, required_role: str) -> None:
    if required_role.upper() == "PITCHER":
        expected_user_id = game.home_user_id if game.is_top_inning else game.away_user_id
    elif required_role.upper() == "BATTER":
        expected_user_id = game.away_user_id if game.is_top_inning else game.home_user_id
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol de juego no válido.")

    # Permitir la ejecución si el turno actual le pertenece al Bot de la CPU
    if expected_user_id == "CPU_BOT":
        return

    if user_id != expected_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No es tu turno. Se esperaba la acción del usuario con rol {required_role}."
        )