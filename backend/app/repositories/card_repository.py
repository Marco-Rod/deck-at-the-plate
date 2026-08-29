"""
Repositorio de cartas de jugador (PlayerCardModel)
===================================================
Centraliza las consultas de cartas usadas por el motor y los routers.
"""
from typing import Iterable, Sequence

from app.core.enums import PITCHER_POSITIONS
from app.models import PlayerCardModel, TacticCard
from app.models.user_data import UserCardInventory


def get_card_by_id(db, card_id) -> "PlayerCardModel | None":
    """
    Retorna la carta de jugador con el id dado, o None si no existe.
    """
    if card_id is None:
        return None
    return db.query(PlayerCardModel).filter(PlayerCardModel.id == card_id).first()


def find_all_cards(db) -> Sequence["PlayerCardModel"]:
    """Retorna todas las cartas de jugador registradas."""
    return db.query(PlayerCardModel).all()


def get_tactic_card_by_id(db, card_id) -> "TacticCard | None":
    """
    Retorna la carta táctica con el id dado, o None si no existe.
    """
    if card_id is None:
        return None
    return db.query(TacticCard).filter(TacticCard.id == card_id).first()


def find_pitchers_for_team(
    db,
    team_id: str | None,
    exclude_ids: Iterable[str] | None = None,
    excluded_id: str | None = None,
) -> Sequence["PlayerCardModel"]:
    """
    Retorna todos los pitchers de un equipo (posiciones SP/RP/CP/TWP),
    excluyendo opcionalmente ciertos ids (p.ej. ya usados y el activo).
    """
    if team_id is None:
        return []
    query = db.query(PlayerCardModel).filter(
        PlayerCardModel.team_id == team_id,
        PlayerCardModel.position.in_(PITCHER_POSITIONS),
    )
    if exclude_ids:
        query = query.filter(PlayerCardModel.id.notin_(list(exclude_ids)))
    if excluded_id is not None:
        query = query.filter(PlayerCardModel.id != excluded_id)
    return query.all()


def find_user_inventory_pitchers(
    db,
    user_id: str,
    excluded_id: str | None = None,
) -> Sequence["PlayerCardModel"]:
    """
    Retorna los pitchers del inventario de un usuario (join con
    UserCardInventory), excluyendo opcionalmente un pitcher activo.
    """
    query = (
        db.query(PlayerCardModel)
        .join(UserCardInventory, UserCardInventory.card_id == PlayerCardModel.id)
        .filter(
            UserCardInventory.user_id == user_id,
            PlayerCardModel.position.in_(PITCHER_POSITIONS),
        )
    )
    if excluded_id is not None:
        query = query.filter(PlayerCardModel.id != excluded_id)
    return query.all()


def count_user_inventory(db, user_id: str) -> int:
    """
    Retorna el número total de cartas del inventario de un usuario.
    """
    return (
        db.query(UserCardInventory)
        .filter(UserCardInventory.user_id == user_id)
        .count()
    )


def find_user_inventory_cards(
    db,
    user_id: str,
    limit: int | None = None,
) -> Sequence["UserCardInventory"]:
    """
    Retorna las filas de inventario de un usuario (opcionalmente limitadas).
    """
    query = db.query(UserCardInventory).filter(UserCardInventory.user_id == user_id)
    if limit is not None:
        query = query.limit(limit)
    return query.all()