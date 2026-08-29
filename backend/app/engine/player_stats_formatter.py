"""
Módulo: player_stats_formatter
=============================
Formatea los atributos de jugadores según su rol para ser mostrados en el frontend.

Para BATEADORES:
  - CON (Contacto): contact attribute
  - POW (Poder): power attribute
  - VIS (Visión): derived from contact (70%) + overall (30%)

Para LANZADORES:
  - VEL (Velocidad): best velocity from repertoire
  - CTA (Control): best control from repertoire
  - MCA (Movimiento): best movement from repertoire
"""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.card import PlayerCardModel


def format_batter_stats(card: "PlayerCardModel") -> List[dict]:
    """
    Formatea los stats de un bateador para mostrar en la tarjeta.
    
    Returns:
        List[{"label": str, "val": int}]
        - CON (Contacto)
        - POW (Poder)
        - VIS (Visión derivada)
    """
    # Calcular visión como en attribute_mapper
    vision = int(card.contact * 0.70 + card.overall * 0.30)
    
    return [
        {"label": "CON", "val": card.contact},
        {"label": "POW", "val": card.power},
        {"label": "VIS", "val": vision},
    ]


def format_pitcher_stats(card: "PlayerCardModel") -> List[dict]:
    """
    Formatea los stats de un lanzador para mostrar en la tarjeta.
    Extrae el mejor pitch de cada categoría del repertorio.
    
    Returns:
        List[{"label": str, "val": int}]
        - VEL (Velocidad más alta del repertorio)
        - CTA (Control más alto del repertorio)
        - MCA (Movimiento más alto del repertorio)
    """
    # Valores por defecto si no hay repertorio
    best_velocity = card.velocity or 75
    best_control = card.control or 70
    best_movement = card.movement or 70
    
    # Si hay repertorio, buscar los mejores valores
    if card.repertoire and len(card.repertoire) > 0:
        velocities = [p.get("velocity", 0) for p in card.repertoire]
        controls = [p.get("control", 0) for p in card.repertoire]
        movements = [p.get("movement", 0) for p in card.repertoire]
        
        if velocities:
            best_velocity = max(velocities)
        if controls:
            best_control = max(controls)
        if movements:
            best_movement = max(movements)
    
    return [
        {"label": "VEL", "val": best_velocity},
        {"label": "CTA", "val": best_control},
        {"label": "MCA", "val": best_movement},
    ]


def format_player_stats(card: "PlayerCardModel", role: str) -> List[dict]:
    """
    Formatea los stats de un jugador según su rol.
    
    Args:
        card: PlayerCardModel de la base de datos
        role: "PITCHER" o "BATTER"
    
    Returns:
        List[{"label": str, "val": int}]
    """
    if role == "PITCHER":
        return format_pitcher_stats(card)
    else:  # BATTER
        return format_batter_stats(card)
