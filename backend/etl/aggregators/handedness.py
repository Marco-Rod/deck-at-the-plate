"""Handedness splits (spec §31): side efectivo OBSERVADO por evento.

Bateador: vs pitcher L/R (p_throws). Lanzador: vs lado del bateador L/R
(stand observado de cada evento, no Player.bats).
"""

from typing import Iterable

from app.core.enums import BatterSide, ThrowHand
from etl.aggregators.metrics import BatterCounter, PitcherCounter


def _hand(throw) -> ThrowHand | None:
    return throw.value if throw else None


def _side(stand) -> str | None:
    if stand is None:
        return None
    code = stand.value
    if code == "S":
        return None  # side efectivo se observa por evento; L/S en raw ya es L o R
    return code


def batter_handedness_rows(player_season_id: str, views: Iterable, *, as_pitches=None) -> list[dict]:
    rows = []
    for hand in (ThrowHand.LEFT, ThrowHand.RIGHT):
        subset = [v.pitch for v in views if _hand(v.pitch.p_throws) == hand]
        counter = BatterCounter(subset)
        if counter.pa <= 0:
            continue
        rows.append(
            {
                "player_season_id": player_season_id,
                "pitcher_hand": hand.value,
                "pa": counter.pa,
                "sample_size": counter.pa,
                "pitches_seen": counter.pitches_seen,
                "swings": counter.swings,
                "whiffs": counter.whiffs,
                "hits": counter.hits,
                "home_runs": counter.home_runs,
                "walks": counter.walks,
                "strikeouts": counter.strikeouts,
                "avg": counter.avg,
                "slg": counter.slg,
                "woba": counter.woba,
                "xwoba": counter.xwoba,
                "contact_rate": counter.contact_rate,
                "whiff_rate": counter.whiff_rate,
                "hard_hit_rate": counter.hard_hit_rate,
            }
        )
    return rows


def pitcher_handedness_rows(player_season_id: str, views: Iterable, *, as_pitches=None) -> list[dict]:
    rows = []
    for side in (BatterSide.LEFT, BatterSide.RIGHT):
        subset = [v.pitch for v in views if _side(v.pitch.stand) == side.value]
        counter = PitcherCounter(subset)
        if counter.p_batters_faced <= 0:
            continue
        rows.append(
            {
                "player_season_id": player_season_id,
                "batter_side": side.value,
                "batters_faced": counter.p_batters_faced,
                "sample_size": counter.p_batters_faced,
                "pitches": counter.pitches_total,
                "swings": counter.swing_outs,
                "whiffs": counter.whiffs,
                "hits_allowed": counter.hits_allowed,
                "home_runs_allowed": counter.home_runs_allowed,
                "walks": counter.walks,
                "strikeouts": counter.strikeouts,
                "woba_allowed": counter.woba_allowed,
                "xwoba_allowed": counter.xwoba_allowed,
                "whiff_rate": counter.whiff_rate,
                "hard_hit_rate_allowed": counter.hard_hit_rate_allowed,
            }
        )
    return rows