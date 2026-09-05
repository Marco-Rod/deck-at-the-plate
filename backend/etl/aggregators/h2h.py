"""BatterPitcherMatchup (spec §32): histórico por par de jugadores reales.

Se construye desde RAW (batter_mlb_id = X AND pitcher_mlb_id = Y). El ETL
almacena hechos + sample_size; el Matchup Engine decide cuánto confiar.
"""

from typing import Iterable
from datetime import date

from etl.aggregators.metrics import BatterCounter
from etl.dto import PitchSourceRecord


def matchup_rows(
    views_by_pair: dict[tuple[PitchSourceRecord, PitchSourceRecord], Iterable],
    *,
    player_ids: dict[int, str],
    season_start: int,
    season_end: int,
    data_end_date: date,
) -> list[dict]:
    rows = []
    for (batter_mlb_id, pitcher_mlb_id), pitches in views_by_pair.items():
        batter_id = player_ids.get(batter_mlb_id)
        pitcher_id = player_ids.get(pitcher_mlb_id)
        if not batter_id or not pitcher_id:
            continue
        counter = BatterCounter(pitches)
        if counter.pa <= 0:
            continue
        rows.append(
            {
                "batter_id": batter_id,
                "pitcher_id": pitcher_id,
                "season_start": season_start,
                "season_end": season_end,
                "data_end_date": data_end_date,
                "plate_appearances": counter.pa,
                "sample_size": counter.pa,
                "at_bats": counter.ab,
                "pitches": counter.pitches_seen,
                "hits": counter.hits,
                "singles": counter.singles,
                "doubles": counter.doubles,
                "triples": counter.triples,
                "home_runs": counter.home_runs,
                "walks": counter.walks,
                "strikeouts": counter.strikeouts,
                "swings": counter.swings,
                "whiffs": counter.whiffs,
                "avg": counter.avg,
                "slg": counter.slg,
                "woba": counter.woba,
                "xwoba": counter.xwoba,
                "hard_hit_rate": counter.hard_hit_rate,
            }
        )
    return rows