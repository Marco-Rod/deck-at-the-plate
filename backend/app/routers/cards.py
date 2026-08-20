from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import PlayerCard, TacticCard
from app.schemas import PlayerCardResponse, TacticCardResponse

router = APIRouter(prefix="/api/v1/cards", tags=["Catálogo y Cartas"])

@router.get("/players", response_model=List[PlayerCardResponse], summary="Obtener catálogo de jugadores")
def get_player_cards(
    role: Optional[str] = Query(None, description="Filtrar por rol: 'Pitcher' o 'Batter'"),
    team: Optional[str] = Query(None, description="Filtrar por nombre de equipo ficticio"),
    db: Session = Depends(get_db)
):
    """
    Retorna la lista de cartas de jugadores. 
    Permite filtrar por rol o por equipo ficticio dentro de los metadatos JSON.
    """
    query = db.query(PlayerCard)
    
    if role:
        query = query.filter(PlayerCard.role == role)
        
    if team:
        # Consulta sobre el campo JSON extra_metadata
        query = query.filter(PlayerCard.extra_metadata["fictional_team"].as_string() == team)
        
    return query.all()

@router.get("/tactics", response_model=List[TacticCardResponse], summary="Obtener mazo de tácticas")
def get_tactic_cards(db: Session = Depends(get_db)):
    """
    Retorna la lista completa de cartas de mejora y tácticas registradas.
    """
    return db.query(TacticCard).all()