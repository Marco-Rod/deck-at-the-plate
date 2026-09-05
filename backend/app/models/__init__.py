"""
Paquete de modelos SQLAlchemy
=============================
Punto de entrada unificado para todos los modelos de la base de datos.
Importar desde aquí garantiza que SQLAlchemy registre todas las tablas
antes de llamar a Base.metadata.create_all().

Uso recomendado:
    from app.models import PlayerCardModel, GameSession, TacticCard
"""
from app.database import Base
from app.models.team import Team
from app.models.card import PlayerCardModel, CardRarity, TacticCard
from app.models.user_data import User, UserWallet, UserCardInventory, UserLineup, UserTeam
from app.models.game import GameSession
from app.models.game_stats import GameEventLog

# --- Modelos nuevos (ref. referencias/nuevos_modelos.docx) ---
from app.models.player import Player, PlayerSeason, PlayerTeamStint
from app.models.etl import DataImportRun, RawPitchEvent
from app.models.player_analytics import (
    BatterSeasonStats,
    PitcherSeasonStats,
    BatterZoneProfile,
    PitcherZoneProfile,
    BatterPitchFamilyProfile,
    PitcherPitchProfile,
    BatterHandednessSplit,
    PitcherHandednessSplit,
    BatterPitcherMatchup,
)
from app.models.card_generation import CardGenerationProfile
from app.models.pitch_log import PitchEventLog

# Permite hacer: "from app.models import PlayerCardModel, GameSession"
__all__ = [
    "Base",
    "Team",
    "PlayerCardModel",
    "CardRarity",
    "TacticCard",
    "User",
    "UserWallet",
    "UserCardInventory",
    "GameSession",
    "UserLineup",
    "UserTeam",
    "GameEventLog",
    # Modelos nuevos
    "Player",
    "PlayerSeason",
    "PlayerTeamStint",
    "DataImportRun",
    "RawPitchEvent",
    "BatterSeasonStats",
    "PitcherSeasonStats",
    "BatterZoneProfile",
    "PitcherZoneProfile",
    "BatterPitchFamilyProfile",
    "PitcherPitchProfile",
    "BatterHandednessSplit",
    "PitcherHandednessSplit",
    "BatterPitcherMatchup",
    "CardGenerationProfile",
    "PitchEventLog",
]