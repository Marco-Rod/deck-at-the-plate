"""
Repositorio de usuarios, wallets, lineups y clubs (UserTeam)
=============================================================
Centraliza las consultas de app.models.user_data usadas por los routers.
"""
from typing import TYPE_CHECKING

from app.models.user_data import User, UserLineup, UserTeam, UserWallet

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session


def get_user_by_id(db: "Session", user_id: str | None) -> "User | None":
    """Retorna el usuario con el id dado, o None si no existe."""
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: "Session", username: str | None) -> "User | None":
    """Retorna el usuario por su nombre de usuario, o None si no existe."""
    if username is None:
        return None
    return db.query(User).filter(User.username == username).first()


def get_wallet_by_user_id(db: "Session", user_id: str | None) -> "UserWallet | None":
    """Retorna la wallet de un usuario, o None si aún no tiene una."""
    if user_id is None:
        return None
    return db.query(UserWallet).filter(UserWallet.user_id == user_id).first()


def get_or_create_wallet(
    db: "Session",
    user_id: str,
    stamps: int = 1000,
    gems: int = 0,
) -> "UserWallet":
    """
    Retorna la wallet del usuario creándola con los valores base si no existe.
    Comportamiento idéntico al de routers/user.py (stamps=1000, gems=0).
    """
    wallet = get_wallet_by_user_id(db, user_id)
    if wallet is not None:
        return wallet
    wallet = UserWallet(user_id=user_id, stamps=stamps, gems=gems)
    db.add(wallet)
    return wallet


def get_active_lineup(db: "Session", user_id: str | None) -> "UserLineup | None":
    """Retorna el lineup activo de un usuario, o None si no tiene ninguno."""
    if user_id is None:
        return None
    return (
        db.query(UserLineup)
        .filter(UserLineup.user_id == user_id, UserLineup.is_active == True)  # noqa: E712  (comportamiento conservado)
        .first()
    )


def get_user_team(db: "Session", user_id: str | None) -> "UserTeam | None":
    """Retorna el club personalizado de un usuario, o None si no tiene uno."""
    if user_id is None:
        return None
    return db.query(UserTeam).filter(UserTeam.user_id == user_id).first()