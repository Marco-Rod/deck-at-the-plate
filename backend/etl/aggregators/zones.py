"""Perfiles por zona 1-9 (spec §27-§28).

Batería: dims (zone, pitcher_hand, pitch_family) con SplitHand ALL + L/R y
PitchFamilySplit ALL + las 3 familias core. Lanzador: dims (zone, batter_side,
pitch_family). Se emite una fila por celda con al menos 1 pitch.
"""

from typing import Iterable

from app.core.enums import PitchFamilySplit, SplitHand
from etl.aggregators.cell import CellCounts

CORE_FAMILIES = (PitchFamilySplit.FASTBALL, PitchFamilySplit.BREAKING, PitchFamilySplit.OFFSPEED)
HANDS = (SplitHand.ALL, SplitHand.LEFT, SplitHand.RIGHT)
FAMILIES = (PitchFamilySplit.ALL,) + CORE_FAMILIES


def _hand_keys(hand_code: str) -> tuple:
    keys = [SplitHand.ALL, SplitHand(hand_code)]
    return keys


def _family_keys(family: str) -> tuple:
    keys = [PitchFamilySplit.ALL.value]
    if family in CORE_FAMILIES:
        keys.append(family)
    return keys


def _bucket_views(views: Iterable) -> dict[tuple, CellCounts]:
    """(zone, hand, family) → CellCounts acumulando ALL + específicos."""
    buckets: dict[tuple, CellCounts] = {}
    for view in views:
        zone = view.pitch.game_zone
        if zone is None:
            continue
        hand_code = (view.pitch.p_throws.value if view.pitch.p_throws else None)
        family = (view.pitch.pitch_family.value if view.pitch.pitch_family else None)
        hand_codes = [SplitHand.ALL.value] if hand_code is None else [h.value for h in _hand_keys(hand_code)]
        family_keys = _family_keys(family)
        for hand in hand_codes:
            for fam in family_keys:
                key = (int(zone), hand, fam)
                cell = buckets.setdefault(key, CellCounts())
                cell.add(view)
    return buckets


def batter_zone_rows(player_season_id: str, views: Iterable) -> list[dict]:
    rows = []
    for (zone, hand, fam), cell in _bucket_views(views).items():
        stats = cell.batter_stats()
        if cell.pitches == 0:
            continue
        rows.append(
            {
                "player_season_id": player_season_id,
                "zone": zone,
                "pitcher_hand": hand or SplitHand.ALL.value,
                "pitch_family": fam,
                "pitches_seen": cell.pitches,
                "sample_size": cell.pitches,
                **{k: v for k, v in stats.items() if k in {"swings", "takes", "whiffs", "contacts", "balls_in_play", "hits", "home_runs"}},
                "avg": stats["avg"],
                "slg": stats["slg"],
                "woba": stats["woba"],
                "xwoba": stats["xwoba"],
                "contact_rate": stats["contact_rate"],
                "whiff_rate": stats["whiff_rate"],
                "hard_hit_rate": stats["hard_hit_rate"],
                "barrel_rate": stats["barrel_rate"],
            }
        )
    return rows


def pitcher_zone_rows(player_season_id: str, views: Iterable) -> list[dict]:
    rows = []
    for (zone, hand, fam), cell in _bucket_views(views).items():
        stats = cell.pitcher_stats()
        if cell.pitches == 0:
            continue
        rows.append(
            {
                "player_season_id": player_season_id,
                "zone": zone,
                "batter_side": hand or SplitHand.ALL.value,
                "pitch_family": fam,
                "pitches": cell.pitches,
                "sample_size": cell.pitches,
                **{k: v for k, v in stats.items() if k in {"swings", "takes", "whiffs", "called_strikes", "balls_in_play"}},
                "woba_allowed": stats["woba_allowed"],
                "xwoba_allowed": stats["xwoba_allowed"],
                "whiff_rate": stats["whiff_rate"],
                "called_strike_rate": stats["called_strike_rate"],
                "hard_hit_rate_allowed": stats["hard_hit_rate_allowed"],
                "barrel_rate_allowed": stats["barrel_rate_allowed"],
            }
        )
    return rows