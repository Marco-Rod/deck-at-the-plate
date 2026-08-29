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


def find_inventory_with_cards(
    db,
    user_id: str,
) -> Sequence[tuple["UserCardInventory", "PlayerCardModel"]]:
    """
    Retorna (fila de inventario, carta) de un usuario en una sola query
    (evita el N+1 de pedir cada carta por separado).
    """
    return (
        db.query(UserCardInventory, PlayerCardModel)
        .join(PlayerCardModel, PlayerCardModel.id == UserCardInventory.card_id)
        .filter(UserCardInventory.user_id == user_id)
        .all()
    )


def find_inventory_entry(
    db,
    user_id: str,
    card_id: str,
) -> "UserCardInventory | None":
    """Retorna la fila de inventario (user_id, card_id) o None si no existe."""
    return (
        db.query(UserCardInventory)
        .filter(UserCardInventory.user_id == user_id, UserCardInventory.card_id == card_id)
        .first()
    )


def add_inventory_item(
    db,
    user_id: str,
    card_id: str,
) -> "UserCardInventory":
    """Crea (sin commit) una fila de inventario para (user_id, card_id)."""
    item = UserCardInventory(user_id=user_id, card_id=card_id)
    db.add(item)
    return item


def find_cards_excluding_team(db, team_id: str) -> Sequence["PlayerCardModel"]:
    """Retorna las cartas de todos los equipos excepto el indicado."""
    return db.query(PlayerCardModel).filter(PlayerCardModel.team_id != team_id).all()


def find_cards_by_rarity(db, rarity) -> Sequence["PlayerCardModel"]:
    """Retorna todas las cartas con la rareza indicada."""
    return db.query(PlayerCardModel).filter(PlayerCardModel.rarity == rarity).all()


def find_any_card(db) -> "PlayerCardModel | None":
    """Retorna una carta arbitraria (fallback), o None si no hay ninguna."""
    return db.query(PlayerCardModel).first()