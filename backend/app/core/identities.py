"""
Identidades públicas determinísticas (plan V2, capas SOURCE vs GAME)
====================================================================
El re-key de `teams` a UUID requiere un esquema estable para backfills
idempotentes: el id de un Team público se deriva de su abreviatura pública
(v.g. "NYM") vía uuid5. Así, una migración puede re-apuntar FKs sin una
columna auxiliar y sync-game-team-mappings puede upsertear por id conocido.
"""
import uuid

# Namespace estable del proyecto para franquicias públicas.
_FRANCHISE_NS = uuid.UUID("6f4f5a70-8a2b-4c3d-9e10-f1a2b3c4d5e6")


def game_team_id_for(public_abbreviation: str) -> str:
    """UUID determinístico para la franquicia pública con esa abreviatura."""
    return str(uuid.uuid5(_FRANCHISE_NS, f"team:{public_abbreviation.upper()}"))