"""Carga de metadata MLB: equipos, rosters, jugadores (spec §7-§9, §23-§24).

Upserts idempotentes por mlb_id / abbreviation; PlayerMetadataCache evita
re-resolver el mismo ID en un run. HTTP fuera de transacción.

Split (plan Card Catalog V1): sync-teams y sync-rosters son comandos separados.
run_teams_and_rosters se conserva como composición para back-compat/tests.
"""

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.core.enums import ImportStatus
from app.core.time import utcnow
from app.models import DataImportRun, Player
from etl.config import ETL_PIPELINE_VERSION
from etl.loaders.core import (
    upsert_player,
    upsert_player_season,
    upsert_player_team_stint,
    upsert_team,
    upsert_team_roster_member,
    upsert_team_roster_snapshot,
)
from etl.sources.mlb import MLBStatsApiClient, PlayerMetadataCache

logger = logging.getLogger("etl.pipelines.metadata")


@dataclass
class MetadataRunResult:
    teams: int = 0
    players: int = 0
    stints: int = 0
    season_snapshots: int = 0
    roster_snapshots: int = 0
    roster_members: int = 0
    unresolved: list[int] = field(default_factory=list)
    import_run_id: str = ""


class MetadataPipeline:
    def __init__(self, db: Session, client: MLBStatsApiClient) -> None:
        self._db = db
        self._client = client
        self._cache = PlayerMetadataCache(client)
        self._result: MetadataRunResult | None = None

    def _begin_run(self, *, season: int, w_from: date, w_to: date) -> DataImportRun:
        run = DataImportRun(
            source="MLB_STATS_API",
            pipeline_version=ETL_PIPELINE_VERSION,
            season=season,
            date_from=w_from,
            date_to=w_to,
            status=ImportStatus.RUNNING,
        )
        self._db.add(run)
        self._db.commit()
        return run

    def _finish_run(self, run: DataImportRun, result: MetadataRunResult) -> None:
        run.status = ImportStatus.SUCCESS if not result.unresolved else ImportStatus.PARTIAL
        if result.unresolved:
            run.error_summary = f"sin resolver: {sorted(result.unresolved)[:50]}"
        run.finished_at = utcnow()
        self._db.commit()

    def _fail_run(self, run: DataImportRun, exc: Exception) -> None:
        self._db.rollback()
        raise exc

    def run_teams(self, *, season: int, data_start_date: date | None = None, data_end_date: date | None = None) -> MetadataRunResult:
        """Sync-teams (§30): upsert los 30 equipos de la temporada. Sin rosters."""
        w_from = data_start_date or date(season, 1, 1)
        w_to = data_end_date or date(season, 12, 31)
        result = MetadataRunResult()
        run = self._begin_run(season=season, w_from=w_from, w_to=w_to)
        result.import_run_id = run.id
        self._result = result
        try:
            teams = self._client.get_teams(season)
            for team in teams:
                upsert_team(self._db, team)
                result.teams += 1
            self._db.commit()
        except Exception as exc:
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
            logger.exception("sync-teams falló")
            run.finished_at = utcnow()
            self._db.commit()
            raise
        self._finish_run(run, result)
        return result

    def run_rosters(
        self,
        *,
        season: int,
        data_start_date: date | None = None,
        data_end_date: date | None = None,
        roster_type: str = "ACTIVE",
        source: str = "MLB_STATS_API",
    ) -> MetadataRunResult:
        """Sync-rosters (§17, §43): players + stints + TeamRosterSnapshot/Members.

        Enumeración por client.get_teams SIN upsert de equipos: los teams los
        mantiene sync-teams. Snapshot idempotente por (team, season, as_of,
        roster_type); fechas distintas generan historial, nunca sobrescriben.
        """
        w_from = data_start_date or date(season, 1, 1)
        w_to = data_end_date or date(season, 12, 31)
        result = MetadataRunResult()
        run = self._begin_run(season=season, w_from=w_from, w_to=w_to)
        result.import_run_id = run.id
        self._result = result
        try:
            teams = self._client.get_teams(season)
            for team in teams:
                roster = self._client.get_roster(team.mlb_team_id, season, as_of=w_to)
                snapshot = upsert_team_roster_snapshot(
                    self._db, team_id=team.abbreviation, season=season, as_of_date=w_to, roster_type=roster_type, source=source
                )
                result.roster_snapshots += 1
                for member in roster:
                    player = self._persist_roster_member(member, season, w_from, w_to, run.id)
                    if player is None:
                        continue
                    upsert_team_roster_member(
                        self._db,
                        snapshot=snapshot,
                        player=player,
                        status=member.status_code,
                        position=member.position_code,
                        jersey_number=member.jersey_number,
                    )
                    result.roster_members += 1
                self._db.commit()
        except Exception as exc:
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
            logger.exception("sync-rosters falló")
            run.finished_at = utcnow()
            self._db.commit()
            raise
        self._finish_run(run, result)
        return result

    def run_teams_and_rosters(self, *, season: int, data_start_date: date, data_end_date: date) -> MetadataRunResult:
        """Back-compat: composición de sync-teams + sync-rosters."""
        teams_result = self.run_teams(season=season, data_start_date=data_start_date, data_end_date=data_end_date)
        rosters_result = self.run_rosters(season=season, data_start_date=data_start_date, data_end_date=data_end_date)
        combined = MetadataRunResult()
        combined.teams = teams_result.teams
        combined.players = rosters_result.players
        combined.stints = rosters_result.stints
        combined.season_snapshots = teams_result.season_snapshots + rosters_result.season_snapshots
        combined.roster_snapshots = rosters_result.roster_snapshots
        combined.roster_members = rosters_result.roster_members
        combined.unresolved = sorted(set(teams_result.unresolved) | set(rosters_result.unresolved))
        combined.import_run_id = rosters_result.import_run_id
        return combined

    def _persist_roster_member(self, member, season, w_from, w_to, run_id) -> Player | None:
        record = self._cache.get_player(member.mlb_id)
        if record is None:
            if self._result is not None:
                self._result.unresolved.append(member.mlb_id)
            logger.warning("mlb_id sin resolver: %s", member.mlb_id)
            return None
        player = upsert_player(self._db, record)
        upsert_player_season(
            self._db, player=player, season=season, data_start_date=w_from, data_end_date=w_to, import_run_id=run_id
        )
        upsert_player_team_stint(
            self._db,
            player=player,
            season=season,
            team_id=member.team_abbreviation,
            start_date=w_from,
            end_date=None,
            is_primary_at_cutoff=True,
        )
        self._db.flush()
        if self._result is not None:
            self._result.players += 1
            self._result.stints += 1
        return player

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
            logger.exception("metadata snapshot falló")
            run.finished_at = utcnow()
            self._db.commit()
            raise
        run.finished_at = utcnow()
        self._db.commit()
        return result

    def resolve_players_from_raw(
        self, *, season: int, data_start_date: date, data_end_date: date
    ) -> MetadataRunResult:
        """Resuelve en BD únicamente los Player que aparecen en RAW (corrección §6).

        mlb_ids distintos del RAW (batter/pitcher) → existentes → resolver por
        cache/API SOLO los faltantes → upsert. Sin consultas de rosters/equipos:
        analytics necesita únicamente Player (+ PlayerSeason, que él mismo
        asegura vía _ensure_player_seasons).
        """
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
            from app.models import RawPitchEvent

            ids = self._db.query(RawPitchEvent.batter_mlb_id).filter(
                RawPitchEvent.season == season,
                RawPitchEvent.game_date >= data_start_date,
                RawPitchEvent.game_date <= data_end_date,
            ).distinct().all()
            ids.extend(
                self._db.query(RawPitchEvent.pitcher_mlb_id)
                .filter(
                    RawPitchEvent.season == season,
                    RawPitchEvent.game_date >= data_start_date,
                    RawPitchEvent.game_date <= data_end_date,
                )
                .distinct()
                .all()
            )
            mlb_ids = {row[0] for row in ids}
            existing = {
                p.mlb_id
                for p in self._db.query(Player).filter(Player.mlb_id.in_(mlb_ids)).all()
            } if mlb_ids else set()
            unknown = sorted(mlb_ids - existing)
            logger.info("resolve players: %s conocidos, %s a resolver", len(existing), len(unknown))

            for mlb_id in unknown:
                self._persist_player_only(mlb_id, season, data_start_date, data_end_date, run.id)
                result.players += 1

            run.status = ImportStatus.SUCCESS if not result.unresolved else ImportStatus.PARTIAL
            if result.unresolved:
                run.error_summary = f"sin resolver: {sorted(result.unresolved)[:50]}"
        except Exception as exc:
            self._db.rollback()
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
            logger.exception("resolve players falló")
            run.finished_at = utcnow()
            self._db.commit()
            raise
        run.finished_at = utcnow()
        self._db.commit()
        return result

    def _persist_player_only(self, mlb_id, season, w_from, w_to, run_id) -> None:
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
        self._db.commit()