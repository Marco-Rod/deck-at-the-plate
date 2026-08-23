from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.schemas import TeamBaseSchema, TeamRosterResponseSchema, PlayerCardSchema
from app.database import get_db
from app.models import PlayerCardModel, Team

router = APIRouter(prefix="/api/v1/cards", tags=["Cards & Rosters"])


@router.get("/teams", response_model=List[TeamBaseSchema])
def get_all_teams(db: Session = Depends(get_db)):
    return db.query(Team).all()


@router.get("/teams/{team_id}", response_model=TeamRosterResponseSchema)
def get_team_roster(team_id: str, db: Session = Depends(get_db)):
    """Devuelve la información de un equipo junto con su plantilla activa de jugadores."""
    formatted_team_id = team_id.upper()
    team = db.query(Team).filter(Team.id == formatted_team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    players = (
        db.query(PlayerCardModel)
        .filter(PlayerCardModel.team_id == formatted_team_id)
        .order_by(PlayerCardModel.overall.desc())
        .all()
    )

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
def get_card_by_id(card_id: str, db: Session = Depends(get_db)):
    """Consulta los atributos detallados de una carta específica por su ID."""
    card = db.query(PlayerCardModel).filter(PlayerCardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    return card