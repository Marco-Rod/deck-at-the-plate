from typing import Dict, Any

def sanitize_state_for_player(
    state_data: Dict[str, Any], 
    requesting_user_id: str, 
    home_user_id: str, 
    away_user_id: str, 
    is_top_inning: bool
) -> Dict[str, Any]:
    """
    Oculta la selección de picheo (tipo y zona) al bateador si el turno aún no se ha resuelto.
    """
    sanitized = dict(state_data or {})
    
    # Determinar qué usuario está lanzando en la entrada actual
    # Entrada Alta = Batea Visitante (Away), Pichea Local (Home)
    # Entrada Baja = Batea Local (Home), Pichea Visitante (Away)
    pitching_user_id = home_user_id if is_top_inning else away_user_id

    # Si quien solicita la información ES EL BATEADOR y hay un picheo guardado
    if requesting_user_id != pitching_user_id and sanitized.get("current_pitch"):
        sanitized["current_pitch"] = {
            "has_pitched": True,  # Confirma que el lanzador ya tiró
            "pitch_type": None,   # Enmascarado
            "zone": None          # Enmascarado
        }

    return sanitized