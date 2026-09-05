"""PitcherPitchProfile (spec §30): perfil por pitch exacto × batter_side.

Alimenta repertoire, usage, velocity, movement, effectiveness y
CardGenerationProfile. usage_rate se calcula contra el total de pitches del
lanzador en el snapshot. pitch_family viene del mapping (un pitch_type
pertenece a una sola familia).
"""

from typing import Iterable

from app.core.enums import PitchFamily, SplitHand
from etl.aggregators.cell import CellCounts

CORE_FAMILIES = (PitchFamily.FASTBALL, PitchFamily.BREAKING, PitchFamily.OFFSPEED, PitchFamily.OTHER)


def _bucket_arsenal(views: Iterable) -> dict[tuple, CellCounts]:
    buckets: dict[tuple, CellCounts] = {}
    for view in views:
        pitch_type = (view.pitch.pitch_type or "").strip().upper()
        if not pitch_type:
            continue
        family = view.pitch.pitch_family
        if family not in CORE_FAMILIES:
            continue
        side_code = view.pitch.stand.value if view.pitch.stand else None
        side_keys = [SplitHand.ALL] if side_code is None else [SplitHand.ALL, SplitHand(side_code)]
        for side in side_keys:
            key = (pitch_type, family.value, side.value)
            cell = buckets.setdefault(key, CellCounts())
            cell.add(view)
    return buckets


def pitcher_pitch_profile_rows(player_season_id: str, views: Iterable, *, total_pitches: int) -> list[dict]:
    rows = []
    buckets = _bucket_arsenal(views)
    for (pitch_type, family, side), cell in sorted(buckets.items()):
        if cell.pitches == 0:
            continue
        stats = cell.arsenal_stats()
        usage = round(cell.pitches / total_pitches, 6) if total_pitches else None
        rows.append(
            {
                "player_season_id": player_season_id,
                "pitch_type": pitch_type,
                "pitch_family": family,
                "batter_side": side,
                "pitch_count": cell.pitches,
                "sample_size": cell.pitches,
                "usage_rate": usage,
                "avg_velocity": stats["avg_velocity"],
                "max_velocity": stats["max_velocity"],
                "avg_spin_rate": stats["avg_spin_rate"],
                "avg_horizontal_break": stats["avg_horizontal_break"],
                "avg_vertical_break": stats["avg_vertical_break"],
                "swings": stats["swings"],
                "whiffs": stats["whiffs"],
                "called_strikes": stats["called_strikes"],
                "balls_in_play": stats["balls_in_play"],
                "whiff_rate": stats["whiff_rate"],
                "chase_rate": stats["chase_rate"],
                "called_strike_rate": stats["called_strike_rate"],
                "woba_allowed": stats["woba_allowed"],
                "xwoba_allowed": stats["xwoba_allowed"],
                "hard_hit_rate_allowed": stats["hard_hit_rate_allowed"],
                "barrel_rate_allowed": stats["barrel_rate_allowed"],
            }
        )
    return rows