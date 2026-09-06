"""Configuración versionada de franquicias públicas (plan V2 §37).

Lee etl/config/game_franchises.yaml: la fuente de verdad del branding público
(una franquicia GAME por franquicia SOURCE/MLB). El id del Team público es
determinístico: uuid5("team:<public_abbreviation>") → backfill estable.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

GAME_FRANCHISES_PATH = Path(__file__).parent / "game_franchises.yaml"


@dataclass(frozen=True)
class GameTeamConfig:
    source_team_external_id: int
    public_abbreviation: str
    slug: str
    name: str
    city: str
    primary_color: str
    secondary_color: str
    logo_asset: str | None = None
    is_cpu: bool = True

    @property
    def game_team_id(self) -> str:
        from app.core.identities import game_team_id_for

        return game_team_id_for(self.public_abbreviation)


def load_game_franchises(path: str | Path | None = None) -> list[GameTeamConfig]:
    source = Path(path) if path else GAME_FRANCHISES_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    entries = raw.get("game_franchises", [])
    return [GameTeamConfig(**entry) for entry in entries]