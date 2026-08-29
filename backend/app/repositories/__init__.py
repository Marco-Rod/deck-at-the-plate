"""
Repositorios (Data Access Layer)
=================================
Encapsulan las consultas ORM para que routers y servicios no dependan
directamente de SQLAlchemy (cumplen DIP: la infraestructura depende del
dominio, no al revés). Los routers reciben la sesión y delegan aquí.

Pauta: los repos NO lanzan HTTPException (eso queda en el router/handler)
y solo devuelven entidades o None.
"""
from app.repositories.game_repository import get_game_by_id, save_game
from app.repositories.card_repository import (
    count_user_inventory,
    find_all_cards,
    find_pitchers_for_team,
    find_user_inventory_cards,
    find_user_inventory_pitchers,
    get_card_by_id,
    get_tactic_card_by_id,
)
from app.repositories.team_repository import (
    find_cards_by_team,
    get_all_teams,
    get_team_by_id,
)
from app.repositories.user_repository import (
    get_active_lineup,
    get_or_create_wallet,
    get_user_by_id,
    get_user_by_username,
    get_user_team,
    get_wallet_by_user_id,
)

__all__ = [
    "get_game_by_id",
    "save_game",
    "count_user_inventory",
    "find_all_cards",
    "find_pitchers_for_team",
    "find_user_inventory_cards",
    "find_user_inventory_pitchers",
    "get_card_by_id",
    "get_tactic_card_by_id",
    "find_cards_by_team",
    "get_all_teams",
    "get_team_by_id",
    "get_active_lineup",
    "get_or_create_wallet",
    "get_user_by_id",
    "get_user_by_username",
    "get_user_team",
    "get_wallet_by_user_id",
]