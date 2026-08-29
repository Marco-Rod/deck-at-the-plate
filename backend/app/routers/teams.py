from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories import find_cards_by_team, get_all_teams
from app.services.team_ratings import compute_team_ratings

router = APIRouter(prefix="/api/v1/teams", tags=["Teams"])

@router.get("/cpu")
def get_cpu_teams(db: Session = Depends(get_db)):
    """Devuelve todos los equipos disponibles como rivales CPU con sus medias globales calculadas."""
    teams = get_all_teams(db)
    result = []

    for team in teams:
        cards = find_cards_by_team(db, team.id)
        if not cards:
            continue

        # CÁLCULO DINÁMICO DE MEDIAS (regla única en services/team_ratings.py)
        ratings = compute_team_ratings(cards, default=80)

        result.append({
            "id": team.id,
            "name": team.name,
            "city": team.city,
            "color": team.primary_color,
            "secondary_color": team.secondary_color,
            "badge": team.id,
            "desc": f"Franquicia • {len(cards)} Jugadores",
            "ovr": ratings["overall"],
            "batOvr": ratings["batOvr"],
            "pitOvr": ratings["pitOvr"]
        })

    return result