"""
models.py — Archivo de compatibilidad (NO agregar definiciones aquí)
=====================================================================
Este archivo existe para que imports de la forma `from app.models import X`
sigan funcionando. Todos los modelos SQLAlchemy viven en app/models/ (directorio).

Estructura del paquete de modelos:
    app/models/team.py      → Team
    app/models/card.py      → PlayerCardModel, TacticCard, CardRarity
    app/models/user_data.py → User, UserWallet, UserCardInventory
    app/models/game.py      → GameSession

Agrega nuevos modelos en el directorio correspondiente y re-expórtalos
desde app/models/__init__.py.
"""

# Re-exportar desde el paquete para compatibilidad hacia atrás
from app.models import (  # noqa: F401 — imports necesarios para que SQLAlchemy registre los modelos
    Base,
    Team,
    PlayerCardModel,
    CardRarity,
    TacticCard,
    User,
    UserWallet,
    UserCardInventory,
    GameSession,
)
