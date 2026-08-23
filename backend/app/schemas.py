"""
schemas.py — Archivo de compatibilidad (NO agregar definiciones aquí)
======================================================================
Este archivo existe únicamente para mantener compatibilidad con imports
de la forma `from app.schemas import ...`.

Todas las definiciones de schemas viven en app/schemas/ (directorio).
Agrega nuevos schemas en el módulo correspondiente dentro de ese directorio
y re-expórtalos desde app/schemas/__init__.py.
"""

# Re-exportar todo desde el paquete app/schemas/
from app.schemas.game import (
    CreateGameRequest,
    GameSessionResponse,
    PlayTacticRequest,
    PitchActionRequest,
    SwingActionRequest,
    PlayResultResponse,
    ChangePitcherRequest,
    StealBaseRequest,
)
from app.schemas.cards import TeamBaseSchema, PlayerCardSchema, TeamRosterResponseSchema
from app.schemas.user import WalletSchema, UserProfileResponseSchema, UserInventoryResponseSchema
from app.schemas.shop import StarterPackResponseSchema, OpenPackResponseSchema

__all__ = [
    "CreateGameRequest",
    "GameSessionResponse",
    "PlayTacticRequest",
    "PitchActionRequest",
    "SwingActionRequest",
    "PlayResultResponse",
    "ChangePitcherRequest",
    "StealBaseRequest",
    "TeamBaseSchema",
    "PlayerCardSchema",
    "TeamRosterResponseSchema",
    "WalletSchema",
    "UserProfileResponseSchema",
    "UserInventoryResponseSchema",
    "StarterPackResponseSchema",
    "OpenPackResponseSchema",
]
