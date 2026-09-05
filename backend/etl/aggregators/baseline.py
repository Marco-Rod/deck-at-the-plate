"""Baseline seasonals (spec §25-§26, fuente única RawPitchEvent)."""

from etl.aggregators.metrics import BatterCounter, PitcherCounter


def batter_season_row(player_season_id: str, counter: BatterCounter) -> dict:
    return {
        "player_season_id": player_season_id,
        "pa": counter.pa,
        "ab": counter.ab,
        "hits": counter.hits,
        "singles": counter.singles,
        "doubles": counter.doubles,
        "triples": counter.triples,
        "home_runs": counter.home_runs,
        "walks": counter.walks,
        "strikeouts": counter.strikeouts,
        "pitches_seen": counter.pitches_seen,
        "swings": counter.swings,
        "whiffs": counter.whiffs,
        "balls_in_play": counter.balls_in_play,
        "avg": counter.avg,
        "obp": counter.obp,
        "slg": counter.slg,
        "ops": counter.ops,
        "woba": counter.woba,
        "xwoba": counter.xwoba,
        "avg_exit_velocity": counter.avg_exit_velocity,
        "avg_launch_angle": counter.avg_launch_angle,
        "hard_hit_rate": counter.hard_hit_rate,
        "barrel_rate": counter.barrel_rate,
        "swing_rate": counter.swing_rate,
        "whiff_rate": counter.whiff_rate,
        "contact_rate": counter.contact_rate,
        "chase_rate": counter.chase_rate,
        "zone_swing_rate": counter.zone_swing_rate,
        "zone_contact_rate": counter.zone_contact_rate,
    }


def pitcher_season_row(player_season_id: str, counter: PitcherCounter) -> dict:
    return {
        "player_season_id": player_season_id,
        "games": len(counter.games),
        "starts": counter.starts,
        "batters_faced": counter.p_batters_faced,
        "pitches": counter.pitches_total,
        "outs_recorded": counter.outs_recorded,
        "hits_allowed": counter.hits_allowed,
        "home_runs_allowed": counter.home_runs_allowed,
        "walks": counter.walks,
        "strikeouts": counter.strikeouts,
        "era": counter.era,
        "whip": counter.whip,
        "woba_allowed": counter.woba_allowed,
        "xwoba_allowed": counter.xwoba_allowed,
        "avg_velocity": counter.avg_velocity,
        "whiff_rate": counter.whiff_rate,
        "chase_rate": counter.chase_rate,
        "called_strike_rate": counter.called_strike_rate,
        "hard_hit_rate_allowed": counter.hard_hit_rate_allowed,
        "barrel_rate_allowed": counter.barrel_rate_allowed,
    }