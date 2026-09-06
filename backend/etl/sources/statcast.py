"""Fuente Statcast / Baseball Savant (spec secciones 3.2, 4, 5, 10, 11, 43).

Reemplazable: nada del pipeline depende directamente del CSV de Savant, sino de
los PitchSourceRecord que produce StatcastSourceAdapter.
"""

import csv
import io
import logging
import math
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from etl.config import BASEBALL_SAVANT_BASE_URL, STATCAST_CHUNK_DAYS, STATCAST_SAFE_ROW_THRESHOLD
from etl.dto import PitchSourceRecord
from etl.http.client import ExternalHttpClient
from etl.sources import PitchSource

logger = logging.getLogger("etl.sources.statcast")

STATCAST_SEARCH_CSV_PATH = "/statcast_search/csv"

REQUIRED_COLUMNS = {
    "game_pk",
    "game_date",
    "at_bat_number",
    "pitch_number",
    "batter",
    "pitcher",
}

# Columnas opcionales que conocemos y mapeamos (las desconocidas se ignoran).
KNOWN_OPTIONAL_COLUMNS = frozenset(
    {
        "balls", "strikes", "outs_when_up", "inning", "inning_topbot",
        "stand", "p_throws", "pitch_type", "release_speed", "release_spin_rate",
        "pfx_x", "pfx_z", "plate_x", "plate_z", "zone", "description", "events",
        "bb_type", "launch_speed", "launch_angle", "estimated_woba_using_speedangle",
        "woba_value", "home_team", "away_team",
    }
)


class StatcastQueryBuilder:
    """Centraliza los parámetros del CSV de Statcast (spec sección 10)."""

    def build_date_range(self, date_from: date, date_to: date, *, player_type: str = "pitcher") -> dict:
        params = {
            "all": "true",
            "type": "details",
            "game_date_gt": date_from.isoformat(),
            "game_date_lt": date_to.isoformat(),
            "player_type": player_type,
        }
        return params

    def build_batter(self, mlb_id: int, date_from: date, date_to: date) -> dict:
        params = self.build_date_range(date_from, date_to, player_type="batter")
        params["batters_lookup[]"] = str(mlb_id)
        return params

    def build_pitcher(self, mlb_id: int, date_from: date, date_to: date) -> dict:
        params = self.build_date_range(date_from, date_to, player_type="pitcher")
        params["pitchers_lookup[]"] = str(mlb_id)
        return params

    def build_game(self, game_pk: int) -> dict:
        return {"game_pk": str(game_pk), "all": "true", "type": "details"}


def split_date_ranges(date_from: date, date_to: date, chunk_days: int = STATCAST_CHUNK_DAYS) -> list[tuple[date, date]]:
    """Divide la ventana en trozos de chunk_days días (spec sección 5)."""
    if date_from > date_to:
        return []
    windows: list[tuple[date, date]] = []
    cursor = date_from
    while cursor <= date_to:
        end = min(cursor + timedelta(days=chunk_days - 1), date_to)
        windows.append((cursor, end))
        cursor = end + timedelta(days=1)
    return windows


def validate_headers(headers: list[str]) -> list[str]:
    """SPEC sección 43: falta requerida → error; columna nueva → ignorar."""
    present = {h.strip().lower() for h in headers}
    missing = REQUIRED_COLUMNS - present
    if missing:
        raise ValueError(f"statcast headers incompletos: faltan {sorted(missing)}")
    unknown = present - REQUIRED_COLUMNS - KNOWN_OPTIONAL_COLUMNS
    if unknown:
        logger.debug("statcast columna nueva ignorada: %s", sorted(unknown))
    return headers


def _to_int(value: str) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _to_decimal(value: str) -> Optional[Decimal]:
    if value is None or value == "" or value in {".", "nan"}:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


class StatcastCSVParser:
    """Parsea el CSV crudo en PitchSourceRecord validando headers."""

    def parse(self, csv_text: str) -> list[PitchSourceRecord]:
        # Baseball Savant puede anteponer un BOM UTF-8 al primer encabezado.
        # Sin retirarlo, csv interpreta la clave como '\ufeff"pitch_type"' y
        # todos los registros pierden silenciosamente el tipo de lanzamiento.
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
        validate_headers(reader.fieldnames or [])
        records = []
        for row in reader:
            if not row or not row.get("game_pk"):
                continue
            records.append(self._row_to_record(row))
        return records

    def _row_to_record(self, row: dict) -> PitchSourceRecord:
        row = {k.strip().lower(): (v or None) for k, v in row.items()}
        return PitchSourceRecord(
            game_pk=_to_int(row.get("game_pk")),
            game_date=_to_date(row.get("game_date")),
            at_bat_number=_to_int(row.get("at_bat_number")),
            pitch_number=_to_int(row.get("pitch_number")),
            batter_mlb_id=_to_int(row.get("batter")),
            pitcher_mlb_id=_to_int(row.get("pitcher")),
            balls=_to_int(row.get("balls")),
            strikes=_to_int(row.get("strikes")),
            outs_when_up=_to_int(row.get("outs_when_up")),
            inning=_to_int(row.get("inning")),
            inning_topbot=row.get("inning_topbot"),
            stand=row.get("stand"),
            p_throws=row.get("p_throws"),
            pitch_type=row.get("pitch_type"),
            release_speed=_to_decimal(row.get("release_speed")),
            release_spin_rate=_to_decimal(row.get("release_spin_rate")),
            pfx_x=_to_decimal(row.get("pfx_x")),
            pfx_z=_to_decimal(row.get("pfx_z")),
            plate_x=_to_decimal(row.get("plate_x")),
            plate_z=_to_decimal(row.get("plate_z")),
            zone=_to_int(row.get("zone")),
            description=row.get("description"),
            events=row.get("events"),
            bb_type=row.get("bb_type"),
            launch_speed=_to_decimal(row.get("launch_speed")),
            launch_angle=_to_decimal(row.get("launch_angle")),
            estimated_woba_using_speedangle=_to_decimal(row.get("estimated_woba_using_speedangle")),
            woba_value=_to_decimal(row.get("woba_value")),
            home_team=row.get("home_team"),
            away_team=row.get("away_team"),
        )


class StatcastSourceAdapter(PitchSource):
    def __init__(
        self,
        http: Optional[ExternalHttpClient] = None,
        query_builder: Optional[StatcastQueryBuilder] = None,
        parser: Optional[StatcastCSVParser] = None,
        base_url: Optional[str] = None,
        chunk_days: int = STATCAST_CHUNK_DAYS,
        safe_row_threshold: int = STATCAST_SAFE_ROW_THRESHOLD,
    ) -> None:
        self._http = http or ExternalHttpClient()
        self._query_builder = query_builder or StatcastQueryBuilder()
        self._parser = parser or StatcastCSVParser()
        self._base_url = (base_url or BASEBALL_SAVANT_BASE_URL).rstrip("/")
        self._chunk_days = chunk_days
        self._safe_row_threshold = safe_row_threshold

    def _csv_url(self) -> str:
        return f"{self._base_url}{STATCAST_SEARCH_CSV_PATH}"

    def _fetch_csv(self, params: dict) -> list[PitchSourceRecord]:
        response = self._http.get(self._csv_url(), params=params)
        response.raise_for_status()
        return self._parser.parse(response.text)

    def get_pitches(self, date_from: date, date_to: date):
        return self.fetch_date_range(date_from, date_to)

    def fetch_date_range(self, date_from: date, date_to: date, *, player_type: str = "pitcher", chunk_days: int | None = None) -> list[PitchSourceRecord]:
        """Ruta pública SEGURA (corrección §3): único punto de acceso por rango.

        Aplica internamente: chunking base (chunk_days o STATCAST_CHUNK_DAYS),
        umbral de seguridad (STATCAST_SAFE_ROW_THRESHOLD) con subdivisión, y
        combinación de subchunks. No existe ruta insegura pública.
        """
        days = chunk_days or self._chunk_days
        build = lambda wf, wt: self._query_builder.build_date_range(wf, wt, player_type=player_type)
        records: list[PitchSourceRecord] = []
        for window_from, window_to in split_date_ranges(date_from, date_to, days):
            records.extend(self._fetch_chunk_guarded(window_from, window_to, build=build))
        return records

    def fetch_date_range_chunked(self, date_from: date, date_to: date) -> list[PitchSourceRecord]:
        """Deprecado: alias de fetch_date_range (ruta segura)."""
        return self.fetch_date_range(date_from, date_to)

    def fetch_batter(self, mlb_id: int, date_from: date, date_to: date) -> list[PitchSourceRecord]:
        build = lambda wf, wt: self._query_builder.build_batter(mlb_id, wf, wt)
        return self._fetch_player_range(date_from, date_to, build)

    def fetch_pitcher(self, mlb_id: int, date_from: date, date_to: date) -> list[PitchSourceRecord]:
        build = lambda wf, wt: self._query_builder.build_pitcher(mlb_id, wf, wt)
        return self._fetch_player_range(date_from, date_to, build)

    def _fetch_player_range(self, date_from: date, date_to: date, build) -> list[PitchSourceRecord]:
        records: list[PitchSourceRecord] = []
        for window_from, window_to in split_date_ranges(date_from, date_to, self._chunk_days):
            records.extend(self._fetch_chunk_guarded(window_from, window_to, build=build))
        return records

    def fetch_game(self, game_pk: int) -> list[PitchSourceRecord]:
        return self._fetch_csv(self._query_builder.build_game(game_pk))

    def _fetch_chunk_guarded(self, window_from: date, window_to: date, *, build) -> list[PitchSourceRecord]:
        records = self._fetch_csv(build(window_from, window_to))
        if len(records) >= self._safe_row_threshold and window_from != window_to:
            half = window_from + timedelta(days=(window_to - window_from).days // 2)
            logger.info(
                "statcast chunk cerca del umbral (%s filas) dividiendo %s..%s",
                len(records),
                window_from,
                window_to,
            )
            return self._fetch_chunk_guarded(window_from, half, build=build) + self._fetch_chunk_guarded(
                half + timedelta(days=1), window_to, build=build
            )
        return records
