"""Fuente MLB Stats API (spec secciones 3.1, 7, 8, 9 y 23).

Client central + extractors de equipos, rosters y jugadores. Todo acceso a la
API MLB pasa por MLBStatsApiClient; nunca se dispersan URLs por el resto del
pipeline.
"""

import logging
from datetime import date
from typing import Optional

from etl.config import MLB_STATS_API_BASE_URL
from etl.dto import PlayerSourceRecord, RosterSourceRecord, TeamSourceRecord
from etl.http.client import ExternalHttpClient, get_json
from etl.sources import PlayerSource, RosterSource, TeamSource

logger = logging.getLogger("etl.sources.mlb")

# Códigos de lado de bateo / mano de lanzar tal como los devuelve la API.
_MLB_BAT_CODE_TO_HANDEDNESS = {"L": "L", "R": "R", "S": "S"}
_MLB_PITCH_CODE_TO_THROW = {"L": "L", "R": "R"}


class MLBStatsApiClient:
    def __init__(self, http: Optional[ExternalHttpClient] = None, base_url: Optional[str] = None) -> None:
        self._http = http or ExternalHttpClient()
        self._base_url = (base_url or MLB_STATS_API_BASE_URL).rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    def get_teams(self, season: int, *, sport_id: int = 1, active_status: str = "Y") -> list[TeamSourceRecord]:
        data = get_json(
            self._http,
            self._url("teams"),
            params={"sportId": sport_id, "season": season, "activeStatus": active_status},
        )
        records = []
        for team in data.get("teams", []):
            records.append(
                TeamSourceRecord(
                    mlb_team_id=int(team["id"]),
                    name=team.get("name") or "",
                    abbreviation=team.get("abbreviation") or "",
                    location_name=team.get("locationName") or team.get("name") or "",
                    active=bool(team.get("active", True)),
                )
            )
        return records

    def get_roster(self, team_mlb_id: int, season: int, as_of: Optional[date] = None) -> list[RosterSourceRecord]:
        params: dict = {"rosterType": "active", "season": season, "hydrate": "person"}
        if as_of is not None:
            params["date"] = as_of.isoformat()
        data = get_json(self._http, self._url(f"teams/{team_mlb_id}/roster"), params=params)
        team_abbr = data.get("roster", None)
        # En algunos casos no viene la abreviatura del equipo en esta respuesta.
        records = []
        for item in data.get("roster", []):
            person = item.get("person", {})
            mlb_id = person.get("id")
            if mlb_id is None:
                continue
            records.append(
                RosterSourceRecord(
                    mlb_id=int(mlb_id),
                    full_name=person.get("fullName") or "",
                    team_abbreviation="",
                    season=season,
                    jersey_number=item.get("jerseyNumber"),
                    position_code=item.get("position", {}).get("code"),
                    status_code=item.get("status", {}).get("code"),
                    as_of=as_of,
                )
            )
        return records

    def get_person(self, mlb_id: int) -> Optional[PlayerSourceRecord]:
        data = get_json(self._http, self._url(f"people/{mlb_id}"))
        people = data.get("people", [])
        if not people:
            return None
        person = people[0]
        game_type = person.get("primaryPosition", {}) or {}
        return PlayerSourceRecord(
            mlb_id=int(person["id"]),
            full_name=person.get("fullName") or "",
            first_name=person.get("firstName"),
            last_name=person.get("lastName"),
            birth_date=self._parse_date(person.get("birthDate")),
            primary_position=game_type.get("abbreviation"),
            bats=_MLB_BAT_CODE_TO_HANDEDNESS.get(person.get("batSide", {}).get("code")) if person.get("batSide") else None,
            throws=_MLB_PITCH_CODE_TO_THROW.get(person.get("pitchHand", {}).get("code")) if person.get("pitchHand") else None,
            is_active=bool(person.get("active", True)),
        )

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


class PlayerMetadataCache(PlayerSource):
    """Cache en memoria por MLB ID durante un run (spec secciones 23 y 44)."""

    def __init__(self, client: MLBStatsApiClient) -> None:
        self._client = client
        self._cache: dict[int, Optional[PlayerSourceRecord]] = {}

    def get_player(self, mlb_id: int) -> PlayerSourceRecord:
        if mlb_id not in self._cache:
            record = self._client.get_person(mlb_id)
            self._cache[mlb_id] = record
            logger.info("mlb player resolved mlb_id=%s present=%s", mlb_id, record is not None)
        return self._cache[mlb_id]

    def unresolved_ids(self) -> list[int]:
        return [mlb_id for mlb_id, record in self._cache.items() if record is None]

    def resolved_count(self) -> int:
        return sum(1 for record in self._cache.values() if record is not None)


class TeamExtractor(TeamSource):
    def __init__(self, client: MLBStatsApiClient) -> None:
        self._client = client

    def get_teams(self, season: int) -> list[TeamSourceRecord]:
        return self._client.get_teams(season)


class RosterExtractor(RosterSource):
    def __init__(self, client: MLBStatsApiClient) -> None:
        self._client = client

    def get_roster(self, team_mlb_id: int, season: int, as_of: Optional[date] = None) -> list[RosterSourceRecord]:
        return self._client.get_roster(team_mlb_id, season, as_of=as_of)