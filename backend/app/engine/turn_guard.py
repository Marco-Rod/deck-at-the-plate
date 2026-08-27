from fastapi import HTTPException, status
from app.models import GameSession

def verify_player_turn(game: GameSession, user_id: str, required_role: str) -> None:
    """
    Verifica si es el turno del usuario según su rol (PITCHER o BATTER) y la entrada (TOP/BOT).
    
    Considera la posición del usuario (HOME/AWAY) guardada en state_data.user_role.
    """
    user_role = game.state_data.get("user_role") if game.state_data else "HOME"
    
    # Determinar qué usuario debe tomar la acción según el rol requerido e inning
    if required_role.upper() == "PITCHER":
        # En TOP: lanza el local (home). En BOT: lanza el visitante (away)
        expected_user_id = game.home_user_id if game.is_top_inning else game.away_user_id
    elif required_role.upper() == "BATTER":
        # En TOP: batea el visitante (away). En BOT: batea el local (home)
        expected_user_id = game.away_user_id if game.is_top_inning else game.home_user_id
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol de juego no válido.")

    # Permitir la ejecución si el turno actual le pertenece al Bot de la CPU
    if expected_user_id == "CPU_BOT":
        return

    if user_id != expected_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No es tu turno. Se esperaba la acción del usuario con rol {required_role}. user_id={user_id}, expected={expected_user_id}, user_role={user_role}, is_top={game.is_top_inning}"
        )