from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Team, PlayerCardModel

router = APIRouter(prefix="/api/v1/teams", tags=["Teams"])

@router.get("/cpu")
def get_cpu_teams(db: Session = Depends(get_db)):
    """Devuelve los equipos CPU disponibles con sus medias globales calculadas."""
    teams = db.query(Team).all()
    result = []

    for team in teams:
        cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team.id).all()
        if not cards:
            continue

        # CÁLCULO DINÁMICO DE MEDIAS
        batters = [c for c in cards if c.position not in ["SP", "RP", "CP"]]
        pitchers = [c for c in cards if c.position in ["SP", "RP", "CP"]]

        bat_ovr = round(sum(c.overall for c in batters) / len(batters)) if batters else 80
        pit_ovr = round(sum(c.overall for c in pitchers) / len(pitchers)) if pitchers else 80
        overall = round((bat_ovr + pit_ovr) / 2)

        result.append({
            "id": team.id,
            "name": team.name,
            "city": team.city,
            "color": team.primary_color,
            "secondary_color": team.secondary_color,
            "badge": team.id,
            "desc": f"Franquicia • {len(cards)} Jugadores",
            "ovr": overall,
            "batOvr": bat_ovr,
            "pitOvr": pit_ovr
        })

    return result