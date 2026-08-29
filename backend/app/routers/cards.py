from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas import TeamBaseSchema, TeamRosterResponseSchema
from app.database import get_db
from app.repositories.card_repository import get_card_by_id as repo_get_card_by_id
from app.repositories.team_repository import (
    find_cards_by_team,
    get_all_teams as repo_get_all_teams,
    get_team_by_id,
)

router = APIRouter(prefix="/api/v1/cards", tags=["Cards & Rosters"])


@router.get("/teams", response_model=List[TeamBaseSchema])
def get_all_teams(db: Session = Depends(get_db)):
    return repo_get_all_teams(db)


@router.get("/teams/{team_id}", response_model=TeamRosterResponseSchema)
def get_team_roster(team_id: str, db: Session = Depends(get_db)):
    """Devuelve la información de un equipo junto con su plantilla activa de jugadores."""
    formatted_team_id = team_id.upper()
    team = get_team_by_id(db, formatted_team_id)

    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    players = find_cards_by_team(db, formatted_team_id, order_by_overall_desc=True)

    return {
        "team": {
            "id": team.id,
            "name": team.name,
            "city": team.city,
            "primary_color": team.primary_color,
            "secondary_color": team.secondary_color,
        },
        "total_players": len(players),
        "roster": players,
    }


@router.get("/{card_id}")
def get_card_details(card_id: str, db: Session = Depends(get_db)):
    """Consulta los atributos detallados de una carta específica por su ID."""
    card = repo_get_card_by_id(db, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    return card