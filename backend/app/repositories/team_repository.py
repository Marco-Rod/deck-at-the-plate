"""
Repositorio de equipos (Team)
==============================
Centraliza las consultas a la tabla Team y sus cartas.
"""
from typing import Sequence, TYPE_CHECKING

from app.models import PlayerCardModel, Team

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


def get_all_teams(db: "Session") -> Sequence["Team"]:
    """Retorna todos los equipos registrados."""
    return db.query(Team).all()


def get_team_by_id(db: "Session", team_id: str | None) -> "Team | None":
    """
    Retorna el equipo con el id dado, o None si no existe.
    Nota: los ids de Team son códigos en mayúsculas; normalízalos antes si es necesario.
    """
    if team_id is None:
        return None
    return db.query(Team).filter(Team.id == team_id).first()


def find_cards_by_team(
    db: "Session",
    team_id: str | None,
    order_by_overall_desc: bool = False,
) -> Sequence["PlayerCardModel"]:
    """
    Retorna las cartas de un equipo, opcionalmente ordenadas por overall desc.
    """
    if team_id is None:
        return []
    query = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team_id)
    if order_by_overall_desc:
        query = query.order_by(PlayerCardModel.overall.desc())
    return query.all()