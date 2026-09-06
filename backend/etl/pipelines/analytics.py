"""Pipeline ANALYTICS desde raw (spec §25-§33, §40, §45).

Rebuild por player_season snapshot: delete + reinsert de todos los perfiles del
jugador en una sola transacción. El H2H se reconstruye por ventana global.
Nunca se consulta Statcast aquí.
"""

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.core.enums import ImportStatus
from app.core.time import utcnow
from app.models import (
    BatterHandednessSplit,
    BatterPitchFamilyProfile,
    BatterPitcherMatchup,
    BatterSeasonStats,
    BatterZoneProfile,
    DataImportRun,
    PitcherHandednessSplit,
    PitcherPitchProfile,
    PitcherSeasonStats,
    PitcherZoneProfile,
    Player,
    PlayerSeason,
    RawPitchEvent,
)
from etl.aggregators import (
    batter_handedness_rows,
    batter_pitch_family_rows,
    batter_season_row,
    batter_zone_rows,
    matchup_rows,
    pitcher_handedness_rows,
    pitcher_pitch_profile_rows,
    pitcher_season_row,
    pitcher_zone_rows,
)
from etl.config import ETL_PIPELINE_VERSION
from etl.validators.analytics import validate_profile

logger = logging.getLogger("etl.pipelines.analytics")

_PROFILE_MODELS = (
    BatterSeasonStats,
    PitcherSeasonStats,
    BatterZoneProfile,
    PitcherZoneProfile,
    BatterPitchFamilyProfile,
    PitcherPitchProfile,
    BatterHandednessSplit,
    PitcherHandednessSplit,
)

_RATE_FIELDS_BY_MODEL = {
    "BatterSeasonStats": ("hard_hit_rate", "barrel_rate", "swing_rate", "whiff_rate", "contact_rate", "chase_rate", "zone_swing_rate", "zone_contact_rate"),
    "PitcherSeasonStats": ("whiff_rate", "chase_rate", "called_strike_rate", "hard_hit_rate_allowed", "barrel_rate_allowed"),
    "BatterZoneProfile": ("contact_rate", "whiff_rate", "hard_hit_rate", "barrel_rate"),
    "PitcherZoneProfile": ("whiff_rate", "called_strike_rate", "hard_hit_rate_allowed", "barrel_rate_allowed"),
    "BatterPitchFamilyProfile": ("contact_rate", "whiff_rate", "hard_hit_rate", "barrel_rate"),
    "PitcherPitchProfile": ("usage_rate", "whiff_rate", "chase_rate", "called_strike_rate", "hard_hit_rate_allowed", "barrel_rate_allowed"),
    "BatterHandednessSplit": ("contact_rate", "whiff_rate", "hard_hit_rate"),
    "PitcherHandednessSplit": ("whiff_rate", "hard_hit_rate_allowed"),
    "BatterPitcherMatchup": ("hard_hit_rate",),
}


class AnalyticsValidationError(Exception):
    pass


@dataclass
class AnalyticsRunResult:
    players_processed: int = 0
    profiles_created: int = 0
    analytics_rejected: int = 0
    import_run_id: str = ""
    details: list[str] = field(default_factory=list)


class AnalyticsPipeline:
    def __init__(self, db: Session) -> None:
        self._db = db

    def rebuild(self, *, season: int, data_start_date: date, data_end_date: date) -> AnalyticsRunResult:
        result = AnalyticsRunResult()
        run = DataImportRun(
            source="ANALYTICS",
            pipeline_version=ETL_PIPELINE_VERSION,
            season=season,
            date_from=data_start_date,
            date_to=data_end_date,
            status=ImportStatus.RUNNING,
        )
        self._db.add(run)
        self._db.commit()
        result.import_run_id = run.id
        try:
            players_in_window = self._ensure_player_seasons(season, data_start_date, data_end_date)
            snapshot_ids = [
                ps.id
                for ps in self._db.query(PlayerSeason)
                .filter(
                    PlayerSeason.season == season,
                    PlayerSeason.data_start_date == data_start_date,
                    PlayerSeason.data_end_date == data_end_date,
                )
                .all()
            ]
            for player_season_id in snapshot_ids:
                result.players_processed += 1
                rows = self._build_snapshot_rows(player_season_id, season, data_start_date, data_end_date)
                self._replace_snapshot(player_season_id, rows, result)
            self._rebuild_matchups(season, data_start_date, data_end_date, result)
            run.status = ImportStatus.SUCCESS
        except Exception as exc:
            self._db.rollback()
            run.status = ImportStatus.FAILED
            run.error_summary = str(exc)[:2000]
            logger.exception("analytics pipeline falló")
            run.finished_at = utcnow()
            self._db.commit()
            raise
        run.finished_at = utcnow()
        self._db.commit()
        return result

    # -------------------------------------------------------------- helpers

    def _ensure_player_seasons(self, season: int, w_from: date, w_to: date) -> list:
        """Crea PlayerSeason del snapshot para cualquier jugador presente en RAW."""
        ids = self._db.query(RawPitchEvent.batter_mlb_id).filter(
            RawPitchEvent.season == season,
            RawPitchEvent.game_date >= w_from,
            RawPitchEvent.game_date <= w_to,
        ).distinct().all()
        ids.extend(
            self._db.query(RawPitchEvent.pitcher_mlb_id)
            .filter(
                RawPitchEvent.season == season,
                RawPitchEvent.game_date >= w_from,
                RawPitchEvent.game_date <= w_to,
            )
            .distinct()
            .all()
        )
        mlb_ids = {row[0] for row in ids}
        players = self._db.query(Player).filter(Player.mlb_id.in_(mlb_ids)).all() if mlb_ids else []
        from etl.loaders.core import upsert_player_season

        for player in players:
            upsert_player_season(
                self._db,
                player=player,
                season=season,
                data_start_date=w_from,
                data_end_date=w_to,
            )
        self._db.commit()
        return players

    def _pitches(self, player: Player, season: int, window_from: date, window_to: date, *, role: str) -> list:
        q = self._db.query(RawPitchEvent).filter(
            RawPitchEvent.season == season,
            RawPitchEvent.game_date >= window_from,
            RawPitchEvent.game_date <= window_to,
        )
        if role == "batter":
            q = q.filter(RawPitchEvent.batter_mlb_id == player.mlb_id)
        else:
            q = q.filter(RawPitchEvent.pitcher_mlb_id == player.mlb_id)
        return q.order_by(RawPitchEvent.game_date, RawPitchEvent.at_bat_number, RawPitchEvent.pitch_number).all()

    def _build_snapshot_rows(self, player_season_id: str, season: int, w_from: date, w_to: date) -> list[tuple[str, dict]]:
        ps = self._db.get(PlayerSeason, player_season_id)
        player = self._db.get(Player, ps.player_id)
        from etl.aggregators.metrics import BatterCounter, PitcherCounter

        rows: list[tuple[str, dict]] = []

        bat_pitches = self._pitches(player, season, w_from, w_to, role="batter")
        if bat_pitches:
            counters = BatterCounter(bat_pitches)
            rows.append(("BatterSeasonStats", batter_season_row(player_season_id, counters)))
            rows.extend(("BatterZoneProfile", r) for r in batter_zone_rows(player_season_id, counters.pitches))
            rows.extend(("BatterPitchFamilyProfile", r) for r in batter_pitch_family_rows(player_season_id, counters.pitches))
            rows.extend(("BatterHandednessSplit", r) for r in batter_handedness_rows(player_season_id, counters.pitches))

        pit_pitches = self._pitches(player, season, w_from, w_to, role="pitcher")
        if pit_pitches:
            counters = PitcherCounter(pit_pitches)
            rows.append(("PitcherSeasonStats", pitcher_season_row(player_season_id, counters)))
            rows.extend(("PitcherZoneProfile", r) for r in pitcher_zone_rows(player_season_id, counters.pitches))
            rows.extend(("PitcherPitchProfile", r) for r in pitcher_pitch_profile_rows(player_season_id, counters.pitches, total_pitches=counters.pitches_total))
            rows.extend(("PitcherHandednessSplit", r) for r in pitcher_handedness_rows(player_season_id, counters.pitches))

        return rows

    def _replace_snapshot(self, player_season_id: str, rows: list[tuple[str, dict]], result: AnalyticsRunResult) -> None:
        for model in _PROFILE_MODELS:
            self._db.query(model).filter(model.player_season_id == player_season_id).delete(synchronize_session=False)
        for model_name, row in rows:
            self._validate(model_name, row)
            self._db.add(_model_for(model_name)(**row))
            result.profiles_created += 1
        self._db.commit()

    def _rebuild_matchups(self, season: int, w_from: date, w_to: date, result: AnalyticsRunResult) -> None:
        pitches = (
            self._db.query(RawPitchEvent)
            .filter(
                RawPitchEvent.season == season,
                RawPitchEvent.game_date >= w_from,
                RawPitchEvent.game_date <= w_to,
            )
            .order_by(RawPitchEvent.batter_mlb_id, RawPitchEvent.pitcher_mlb_id, RawPitchEvent.at_bat_number, RawPitchEvent.pitch_number)
            .all()
        )
        pair_map: dict[tuple[int, int], list] = {}
        mlb_ids = set()
        for pitch in pitches:
            pair_map.setdefault((pitch.batter_mlb_id, pitch.pitcher_mlb_id), []).append(pitch)
            mlb_ids.add(pitch.batter_mlb_id)
            mlb_ids.add(pitch.pitcher_mlb_id)
        if not pair_map:
            return

        player_ids = {
            p.mlb_id: p.id for p in self._db.query(Player).filter(Player.mlb_id.in_(mlb_ids)).all()
        }
        self._db.query(BatterPitcherMatchup).filter(
            BatterPitcherMatchup.season_start == season,
            BatterPitcherMatchup.season_end == season,
            BatterPitcherMatchup.data_end_date == w_to,
        ).delete(synchronize_session=False)

        matchup_ids = {mlb_id: player_ids[mlb_id] for mlb_id in mlb_ids if mlb_id in player_ids}
        for pair, pair_pitches in pair_map.items():
            if pair[0] not in matchup_ids or pair[1] not in matchup_ids:
                continue
            rows = matchup_rows(
                {pair: pair_pitches},
                player_ids=matchup_ids,
                season_start=season,
                season_end=season,
                data_end_date=w_to,
            )
            for row in rows:
                self._validate("BatterPitcherMatchup", row)
                self._db.add(BatterPitcherMatchup(**row))
                result.profiles_created += 1
        self._db.commit()

    def _validate(self, model_name: str, row: dict) -> None:
        errors = validate_profile(row, rate_fields=_RATE_FIELDS_BY_MODEL.get(model_name, ()), non_negative_fields=())
        if errors:
            raise AnalyticsValidationError(f"{model_name}: {errors}")


def _model_for(name: str):
    mapping = {
        "BatterSeasonStats": BatterSeasonStats,
        "PitcherSeasonStats": PitcherSeasonStats,
        "BatterZoneProfile": BatterZoneProfile,
        "PitcherZoneProfile": PitcherZoneProfile,
        "BatterPitchFamilyProfile": BatterPitchFamilyProfile,
        "PitcherPitchProfile": PitcherPitchProfile,
        "BatterHandednessSplit": BatterHandednessSplit,
        "PitcherHandednessSplit": PitcherHandednessSplit,
        "BatterPitcherMatchup": BatterPitcherMatchup,
    }
    return mapping[name]