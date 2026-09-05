"""Carga de metadata MLB: equipos, rosters, jugadores (spec §7-§9, §23-§24).

Upserts idempotentes por mlb_id / abbreviation; PlayerMetadataCache evita
re-resolver el mismo ID en un run. HTTP fuera de transacción.
"""

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.core.enums import ImportStatus
from app.core.time import utcnow
from app.models import DataImportRun
from etl.config import ETL_PIPELINE_VERSION
from etl.loaders.core import upsert_player, upsert_player_season, upsert_player_team_stint, upsert_team
from etl.sources.mlb import MLBStatsApiClient, PlayerMetadataCache

logger = logging.getLogger("etl.pipelines.metadata")


@dataclass
class MetadataRunResult:
    teams: int = 0
    players: int = 0
    stints: int = 0
    season_snapshots: int = 0
    unresolved: list[int] = field(default_factory=list)
    import_run_id: str = ""


class MetadataPipeline:
    def __init__(self, db: Session, client: MLBStatsApiClient) -> None:
        self._db = db
        self._client = client
        self._cache = PlayerMetadataCache(client)
        self._result: MetadataRunResult | None = None

    def run_teams_and_rosters(self, *, season: int, data_start_date: date, data_end_date: date) -> MetadataRunResult:
        result = MetadataRunResult()
        run = DataImportRun(
            source="MLB_STATS_API",
            pipeline_version=ETL_PIPELINE_VERSION,
            season=season,
            date_from=data_start_date,
            date_to=data_end_date,
            status=ImportStatus.RUNNING,
        )
        self._db.add(run)
        self._db.commit()
        result.import_run_id = run.id
        self._result = result
        try:
            teams = self._client.get_teams(season)
            team_ids = set()
            for team in teams:
                upsert_team(self._db, team)
                team_ids.add(team.mlb_team_id)
                result.teams += 1
            self._db.commit()

            roster_player_ids: set[int] = set()
            stints_by_player: dict[int, list] = {}
            for team in teams:
                roster = self._client.get_roster(team.mlb_team_id, season, as_of=data_end_date)
                for member in roster:
                    roster_player_ids.add(member.mlb_id)
                    stints_by_player.setdefault(member.mlb_id, []).append((team.abbreviation, member))
            self._db.commit()

            for mlb_id in roster_player_ids:
                self._persist_player_and_snapshot(
                    mlb_id, season, data_start_date, data_end_date, run.id, stints_by_player.get(mlb_id, [])
                )

            run.status = ImportStatus.SUCCESS if not result.unresolved else ImportStatus.PARTIAL
            if result.unresolved:
                run.error_summary = f"sin resolver: {sorted(result.unresolved)[:50]}"
        except Exception as exc:
            self._db.rollback()
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
            logger.exception("metadata pipeline falló")
        finally:
            run.finished_at = utcnow()
            self._db.commit()
        return result

    def _persist_player_and_snapshot(self, mlb_id, season, w_from, w_to, run_id, rosters) -> None:
        record = self._cache.get_player(mlb_id)
        if record is None:
            if self._result is not None:
                self._result.unresolved.append(mlb_id)
            logger.warning("mlb_id sin resolver: %s", mlb_id)
            return
        player = upsert_player(self._db, record)
        upsert_player_season(
            self._db, player=player, season=season, data_start_date=w_from, data_end_date=w_to, import_run_id=run_id
        )
        for team_abbr, member in rosters:
            upsert_player_team_stint(
                self._db,
                player=player,
                season=season,
                team_id=team_abbr,
                start_date=w_from,
                end_date=None,
                is_primary_at_cutoff=True,
            )
        self._db.commit()

    def run_season_snapshot_for(
        self, player_mlb_id: int, *, season: int, data_start_date: date, data_end_date: date
    ) -> MetadataRunResult:
        result = MetadataRunResult()
        run = DataImportRun(
            source="MLB_STATS_API",
            pipeline_version=ETL_PIPELINE_VERSION,
            season=season,
            date_from=data_start_date,
            date_to=data_end_date,
            status=ImportStatus.RUNNING,
        )
        self._db.add(run)
        self._db.commit()
        result.import_run_id = run.id
        self._result = result
        try:
            self._persist_player_and_snapshot(player_mlb_id, season, data_start_date, data_end_date, run.id, [])
            run.status = ImportStatus.SUCCESS
        except Exception as exc:
            self._db.rollback()
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
        finally:
            run.finished_at = utcnow()
            self._db.commit()
        return result