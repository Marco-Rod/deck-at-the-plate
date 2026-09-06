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
    Retorna el equipo con el UUID dado, o None si no existe.
    """
    if team_id is None:
        return None
    return db.query(Team).filter(Team.id == team_id).first()


def resolve_team_to_uuid(db: "Session", team_ref: str | None) -> str | None:
    """
    Traduce una referencia pública a la clave interna (UUID) de Team.

    Durante la transición V2 las rutas públicas siguen usando la abreviatura
    ("LAD"); internamente todo filtra por Team.id (UUID GAME). Un UUID ya
    resuelto se devuelve tal cual.
    """
    if not team_ref:
        return None
    ref = str(team_ref).strip()
    if len(ref) == 36:
        return ref
    team = db.query(Team).filter(Team.abbreviation == ref.upper()).first()
    return team.id if team else None


def get_team_by_ref(db: "Session", team_ref: str | None) -> "Team | None":
    """Retorna el Team público por abreviatura o UUID (None si no existe)."""
    team_id = resolve_team_to_uuid(db, team_ref)
    if team_id is None:
        return None
    return get_team_by_id(db, team_id)


def find_cards_by_team(
    db: "Session",
    team_ref: str | None,
    order_by_overall_desc: bool = False,
) -> Sequence["PlayerCardModel"]:
    """
    Retorna las cartas de un equipo (por abreviatura pública o UUID),
    opcionalmente ordenadas por overall desc.
    """
    team_id = resolve_team_to_uuid(db, team_ref)
    if team_id is None:
        return []
    query = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team_id)
    if order_by_overall_desc:
        query = query.order_by(PlayerCardModel.overall.desc())
    return query.all()