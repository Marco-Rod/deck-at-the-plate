"""Interfaces de fuentes externas (spec sección 56).

Los pipelines dependen de estas abstracciones, no de Baseball Savant ni de la
MLB Stats API directamente.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, Optional

from etl.dto import PitchSourceRecord, PlayerSourceRecord, RosterSourceRecord, TeamSourceRecord


class PlayerSource(ABC):
    @abstractmethod
    def get_player(self, mlb_id: int) -> PlayerSourceRecord:
        ...


class RosterSource(ABC):
    @abstractmethod
    def get_roster(
        self,
        team_mlb_id: int,
        season: int,
        as_of: Optional[date] = None,
    ) -> list[RosterSourceRecord]:
        ...


class TeamSource(ABC):
    @abstractmethod
    def get_teams(self, season: int) -> list[TeamSourceRecord]:
        ...


class PitchSource(ABC):
    @abstractmethod
    def get_pitches(
        self,
        date_from: date,
        date_to: date,
    ) -> Iterable[PitchSourceRecord]:
        ...