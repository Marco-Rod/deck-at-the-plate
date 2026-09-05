"""Cómputo de métricas por snapshot desde RawPitchEvent (spec secciones 25-26).

Única fuente de verdad: RAW. Los agregadores de perfiles consumen estos
contadores, nunca Statcast de nuevo (spec §47).
"""

from dataclasses import dataclass
from typing import Iterable, Optional

from app.models import RawPitchEvent
from etl.normalizers.pitch_result import is_swing, is_whiff

# Terminal events normalizados de Statcast.
_HIT_EVENTS = {"single", "double", "triple", "home_run"}
_WALK_EVENTS = {"walk", "intent_walk", "walk_batter"}
_HBP_EVENTS = {"hit_by_pitch", "hit_by_pitch_blocked"}
_SAC_EVENTS = {"sac_fly", "sac_bunt", "sacrifice_bunt_double_play", "sacrifice_fly_double_play"}
_SO_EVENTS = {"strikeout", "strikeout_double_play"}
_EVENT_OUTS = {
    "strikeout": 1,
    "field_out": 1,
    "force_out": 1,
    "grounded_into_double_play": 2,
    "trade": 0,
    "sac_fly": 1,
    "sac_bunt": 1,
    "sacrifice_fly_double_play": 2,
    "sacrifice_bunt_double_play": 2,
    "double_play": 2,
    "triple_play": 3,
}
_HARD_HIT_VELO = 95.0


def event_is_hit(event: Optional[str]) -> bool:
    return (event or "").lower() in _HIT_EVENTS


def event_outs(event: Optional[str]) -> int:
    return _EVENT_OUTS.get((event or "").lower(), 0)


def is_barrel(launch_speed: Optional[float], launch_angle: Optional[float]) -> bool:
    if launch_speed is None or launch_angle is None:
        return False
    return launch_speed >= 97.5 and 24 <= launch_angle <= 33


def _f(value) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def rate(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _avg(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


@dataclass
class PitchView:
    """Vista derivada mínima de cada pitch para los contadores."""

    pitch: RawPitchEvent
    swing: bool
    whiff: bool
    contact: bool
    in_play: bool
    called_strike: bool
    take: bool
    in_zone: bool
    outside_zone: bool
    hard_hit: bool
    barrel: bool


def _view(pitch: RawPitchEvent) -> PitchView:
    description = pitch.description or ""
    swing = is_swing(description)
    whiff = is_whiff(description)
    in_play = description.lower().startswith("hit_into_play") if description else False
    called_strike = description.lower() == "called_strike"
    in_zone = pitch.game_zone is not None
    launch_speed = _f(pitch.launch_speed)
    launch_angle = _f(pitch.launch_angle)
    return PitchView(
        pitch=pitch,
        swing=swing,
        whiff=whiff,
        contact=swing and not whiff,
        in_play=in_play,
        called_strike=called_strike,
        take=not swing,
        in_zone=in_zone,
        outside_zone=not in_zone,
        hard_hit=in_play and launch_speed is not None and launch_speed >= _HARD_HIT_VELO,
        barrel=in_play and is_barrel(launch_speed, launch_angle),
    )


class _AtBatroll:
    """Acumulador por at-bat (terminal = pitch con mayúsculo? use max pitch_number)."""

    __slots__ = ("pitches", "terminal_pitch")

    def __init__(self) -> None:
        self.pitches: list[PitchView] = []
        self.terminal_pitch: Optional[PitchView] = None


class PitcherCounter:
    """Métricas de un snapshot de lanzador (spec §26)."""

    def __init__(self, pitches: Iterable[RawPitchEvent]) -> None:
        pitches = list(pitches)
        views = [_view(p) for p in pitches]
        self.pitches = views

        self.pitches_total = len(views)
        self.games = {p.pitch.game_pk for p in views}
        self.starts = sum(
            1
            for game_pk in self.games
            if any(p.pitch.inning == 1 for p in views if p.pitch.game_pk == game_pk)
        )
        self.p_batters_faced, self.outs_recorded = self._terminal_counts(views)

        self.strike_outs = sum(1 for p in views if p.called_strike)
        self.swing_outs = sum(1 for p in views if p.swing)
        self.whiffs = sum(1 for p in views if p.whiff)
        self.hits_allowed = 0
        self.home_runs_allowed = 0
        self.walks = 0
        self.strikeouts = 0
        self._populate_events(views)

        speeds = [_f(p.pitch.release_speed) for p in views if p.pitch.release_speed is not None]
        spin = [_f(p.pitch.release_spin_rate) for p in views if p.pitch.release_spin_rate is not None]
        self.avg_velocity = round(_avg(speeds), 2) if speeds else None
        self.max_velocity = round(max(speeds), 2) if speeds else None
        self.avg_spin_rate = round(_avg(spin), 2) if spin else None

        bip_views = [p for p in views if p.in_play]
        self.balls_in_play = len(bip_views)
        self.hard_hit_allowed = sum(1 for p in bip_views if p.hard_hit)
        self.barrels_allowed = sum(1 for p in bip_views if p.barrel)

        in_zone_views = [p for p in views if p.in_zone]
        out_zone_views = [p for p in views if p.outside_zone]
        self.chase = sum(1 for p in out_zone_views if p.swing)
        self.zone_swings = sum(1 for p in in_zone_views if p.swing)

        self.whiff_rate = rate(self.whiffs, self.swing_outs)
        self.chase_rate = rate(self.chase, len(out_zone_views))
        self.called_strike_rate = rate(self.strike_outs, len(views))
        self.hard_hit_rate_allowed = rate(self.hard_hit_allowed, len(bip_views))
        self.barrel_rate_allowed = rate(self.barrels_allowed, len(bip_views))

        woba_values = [_f(p.pitch.estimated_woba) for p in views if p.pitch.estimated_woba is not None]
        xwoba_values = [_f(p.pitch.estimated_woba) for p in views if p.pitch.estimated_woba is not None]
        self.woba_allowed = _avg(woba_values)
        self.xwoba_allowed = _avg(xwoba_values)

        self.era = None  # requiere runs por juego; se deja NULL en V1
        self.whip = self._whip()

    def _whip(self) -> Optional[float]:
        innings = (self.outs_recorded or 0) / 3.0
        if innings <= 0:
            return None
        return round((self.walks + self.hits_allowed) / innings, 4)

    def _terminal_counts(self, views) -> tuple[int, int]:
        atbats: dict[tuple, _AtBatroll] = {}
        for v in views:
            key = (v.pitch.game_pk, v.pitch.at_bat_number)
            roll = atbats.setdefault(key, _AtBatroll())
            roll.pitches.append(v)
            if roll.terminal_pitch is None or v.pitch.pitch_number > roll.terminal_pitch.pitch.pitch_number:
                roll.terminal_pitch = v
        outs = 0
        for roll in atbats.values():
            outs += event_outs(roll.terminal_pitch.pitch.event)
        return len(atbats), outs

    def _populate_events(self, views) -> None:
        atbats: dict[tuple, _AtBatroll] = {}
        for v in views:
            key = (v.pitch.game_pk, v.pitch.at_bat_number)
            roll = atbats.setdefault(key, _AtBatroll())
            if roll.terminal_pitch is None or v.pitch.pitch_number > roll.terminal_pitch.pitch.pitch_number:
                roll.terminal_pitch = v
        for roll in atbats.values():
            event = (roll.terminal_pitch.pitch.event or "").lower()
            if event in _HIT_EVENTS:
                self.hits_allowed += 1
            if event == "home_run":
                self.home_runs_allowed += 1
            if event in _WALK_EVENTS:
                self.walks += 1
            if event in _SO_EVENTS:
                self.strikeouts += 1


class BatterCounter:
    """Métricas de un snapshot de bateador (spec §25)."""

    def __init__(self, pitches: Iterable[RawPitchEvent]) -> None:
        pitches = list(pitches)
        self.pitches = [_view(p) for p in pitches]
        views = self.pitches

        self.pitches_seen = len(views)
        self.swings = sum(1 for p in views if p.swing)
        self.whiffs = sum(1 for p in views if p.whiff)
        self.balls_in_play = sum(1 for p in views if p.in_play)

        self.pa = 0
        self.ab = 0
        self.hits = 0
        self.singles = 0
        self.doubles = 0
        self.triples = 0
        self.home_runs = 0
        self.walks = 0
        self.strikeouts = 0
        self._sacrifices = 0
        self._hbps = 0
        self._outs = 0
        self._populate_events(views)

        hard = [p for p in views if p.in_play and p.hard_hit]
        barrels = [p for p in views if p.in_play and p.barrel]
        self.hard_hit_rate = rate(len(hard), self.balls_in_play)
        self.barrel_rate = rate(len(barrels), self.balls_in_play)

        in_zone = [p for p in views if p.in_zone]
        out_zone = [p for p in views if p.outside_zone]
        self.chase = sum(1 for p in out_zone if p.swing)
        self.zone_swings = sum(1 for p in in_zone if p.swing)
        self.zone_contacts = sum(1 for p in in_zone if p.swing and not p.whiff)

        self.swing_rate = rate(self.swings, self.pitches_seen)
        self.whiff_rate = rate(self.whiffs, self.swings)
        self.contact_rate = rate(self.swings - self.whiffs, self.swings)
        self.chase_rate = rate(self.chase, len(out_zone))
        self.zone_swing_rate = rate(self.zone_swings, len(in_zone))
        self.zone_contact_rate = rate(self.zone_contacts, self.zone_swings)

        exits = [_f(p.pitch.launch_speed) for p in views if p.pitch.launch_speed is not None]
        angles = [_f(p.pitch.launch_angle) for p in views if p.pitch.launch_angle is not None]
        self.avg_exit_velocity = round(_avg(exits), 2) if exits else None
        self.avg_launch_angle = round(_avg(angles), 2) if angles else None

        woba = [_f(p.pitch.estimated_woba) for p in views if p.pitch.estimated_woba is not None]
        self.woba = _avg(woba)
        self.xwoba = _avg(woba)

        self.avg = self._avg()
        self.obp = self._obp()
        self.slg = self._slg()
        self.ops = self._ops()

    def _populate_events(self, views) -> None:
        atbats: dict[tuple, _AtBatroll] = {}
        for v in views:
            key = (v.pitch.game_pk, v.pitch.at_bat_number)
            roll = atbats.setdefault(key, _AtBatroll())
            if roll.terminal_pitch is None or v.pitch.pitch_number > roll.terminal_pitch.pitch.pitch_number:
                roll.terminal_pitch = v
        for roll in atbats.values():
            event = (roll.terminal_pitch.pitch.event or "").lower()
            self.pa += 1
            if event in _WALK_EVENTS:
                self.walks += 1
            elif event in _HBP_EVENTS:
                self._hbps += 1
            elif event in _SAC_EVENTS:
                self._sacrifices += 1
            elif event in _SO_EVENTS:
                self.strikeouts += 1
            if event in _HIT_EVENTS:
                self.hits += 1
                if event == "single":
                    self.singles += 1
                elif event == "double":
                    self.doubles += 1
                elif event == "triple":
                    self.triples += 1
                elif event == "home_run":
                    self.home_runs += 1

        self.ab = self.pa - self.walks - self._hbps - self._sacrifices

    def _avg(self) -> Optional[float]:
        if self.ab <= 0:
            return None
        return round(self.hits / self.ab, 5)

    def _obp(self) -> Optional[float]:
        denom = self.ab + self.walks + self._hbps + self._sacrifices
        if denom <= 0:
            return None
        return round((self.hits + self.walks + self._hbps) / denom, 5)

    def _slg(self) -> Optional[float]:
        if self.ab <= 0:
            return None
        tb = self.singles + 2 * self.doubles + 3 * self.triples + 4 * self.home_runs
        return round(tb / self.ab, 5)

    def _ops(self) -> Optional[float]:
        if self.obp is None or self.slg is None:
            return None
        return round(self.obp + self.slg, 5)