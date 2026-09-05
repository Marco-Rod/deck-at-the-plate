"""DTOs de fuentes externas (spec sección 57).

Aíslan el pipeline de cambios en los formatos externos: los extractors
producen estos dataclasses y el resto del pipeline nunca ve JSON/CSV crudos.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class TeamSourceRecord:
    mlb_team_id: int
    name: str
    abbreviation: str
    location_name: str
    active: bool


@dataclass(frozen=True)
class PlayerSourceRecord:
    mlb_id: int
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    primary_position: Optional[str] = None
    bats: Optional[str] = None  # L / R / S
    throws: Optional[str] = None  # L / R
    is_active: bool = True


@dataclass(frozen=True)
class RosterSourceRecord:
    mlb_id: int
    full_name: str
    team_abbreviation: str
    season: int
    jersey_number: Optional[str] = None
    position_code: Optional[str] = None
    status_code: Optional[str] = None
    as_of: Optional[date] = None  # para snapshots históricos


@dataclass(frozen=True)
class PitchSourceRecord:
    """Un lanzamiento tal como lo devuelve la fuente (Statcast CSV)."""

    game_pk: int
    game_date: date
    at_bat_number: int
    pitch_number: int
    batter_mlb_id: int
    pitcher_mlb_id: int
    balls: Optional[int] = None
    strikes: Optional[int] = None
    outs_when_up: Optional[int] = None
    inning: Optional[int] = None
    inning_topbot: Optional[str] = None
    stand: Optional[str] = None  # L / R
    p_throws: Optional[str] = None  # L / R
    pitch_type: Optional[str] = None
    release_speed: Optional[Decimal] = None
    release_spin_rate: Optional[Decimal] = None
    pfx_x: Optional[Decimal] = None
    pfx_z: Optional[Decimal] = None
    plate_x: Optional[Decimal] = None
    plate_z: Optional[Decimal] = None
    zone: Optional[int] = None  # statcast_zone
    description: Optional[str] = None
    events: Optional[str] = None
    bb_type: Optional[str] = None
    launch_speed: Optional[Decimal] = None
    launch_angle: Optional[Decimal] = None
    estimated_woba_using_speedangle: Optional[Decimal] = None
    woba_value: Optional[Decimal] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None

    @property
    def natural_key(self) -> tuple:
        return (self.game_pk, self.at_bat_number, self.pitch_number)

    @property
    def season(self) -> int:
        return self.game_date.year