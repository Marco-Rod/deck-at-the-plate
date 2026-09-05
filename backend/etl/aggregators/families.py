"""BatterPitchFamilyProfile (spec §29): resumen del bateador por familia core."""

from typing import Iterable

from app.core.enums import PitchFamily, PitchFamilySplit, SplitHand
from etl.aggregators.cell import CellCounts

HANDS = (SplitHand.ALL, SplitHand.LEFT, SplitHand.RIGHT)


def _bucket_family(views: Iterable) -> dict[tuple, CellCounts]:
    buckets: dict[tuple, CellCounts] = {}
    for view in views:
        hand_code = view.pitch.p_throws.value if view.pitch.p_throws else None
        pitch_family = view.pitch.pitch_family
        if pitch_family not in (PitchFamily.FASTBALL, PitchFamily.BREAKING, PitchFamily.OFFSPEED):
            family_key = None
        else:
            family_key = pitch_family.value
        hand_keys = [SplitHand.ALL] if hand_code is None else [SplitHand.ALL, SplitHand(hand_code)]
        for hand in hand_keys:
            key = (hand.value, family_key)
            cell = buckets.setdefault(key, CellCounts())
            cell.add(view)
    return buckets


def batter_pitch_family_rows(player_season_id: str, views: Iterable) -> list[dict]:
    rows = []
    for (hand, family_key), cell in _bucket_family(views).items():
        if cell.pitches == 0:
            continue
        if family_key is None:
            continue  # solo familia core (PitchFamily no admite ALL en columnas)
        stats = cell.batter_stats()
        rows.append(
            {
                "player_season_id": player_season_id,
                "pitch_family": family_key,
                "pitcher_hand": hand,
                "pitches_seen": cell.pitches,
                "sample_size": cell.pitches,
                "swings": stats["swings"],
                "whiffs": stats["whiffs"],
                "balls_in_play": stats["balls_in_play"],
                "hits": stats["hits"],
                "home_runs": stats["home_runs"],
                "woba": stats["woba"],
                "xwoba": stats["xwoba"],
                "contact_rate": stats["contact_rate"],
                "whiff_rate": stats["whiff_rate"],
                "hard_hit_rate": stats["hard_hit_rate"],
                "barrel_rate": stats["barrel_rate"],
            }
        )
    return rows