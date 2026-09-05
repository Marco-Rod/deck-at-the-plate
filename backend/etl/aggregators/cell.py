"""Contador de celda para perfiles por dimensión (spec §27-§31).

Una misma celda (zona × mano × familia, familia × mano, pitch_type × side)
se cuenta de forma idéntica para bateador y lanzador; las diferencias de rol
están en cómo se redondean y nombran las tasas.
"""

from typing import Optional

from etl.aggregators.metrics import event_is_hit, is_barrel, rate, _f, _avg


class CellCounts:
    """Acumulador de una celda de perfil."""

    __slots__ = (
        "pitches", "swings", "whiffs", "takes", "called_strikes",
        "balls_in_play", "hits", "home_runs", "hard_hits", "barrels",
        "out_zone_pitches", "out_zone_swings",
        "exit_speeds", "launch_angles", "wobas",
        "speeds", "spins", "pfx_x", "pfx_z",
    )

    def __init__(self) -> None:
        self.pitches = 0
        self.swings = 0
        self.whiffs = 0
        self.takes = 0
        self.called_strikes = 0
        self.balls_in_play = 0
        self.hits = 0
        self.home_runs = 0
        self.hard_hits = 0
        self.barrels = 0
        self.out_zone_pitches = 0
        self.out_zone_swings = 0
        self.exit_speeds: list[float] = []
        self.launch_angles: list[float] = []
        self.wobas: list[float] = []
        self.speeds: list[float] = []
        self.spins: list[float] = []
        self.pfx_x: list[float] = []
        self.pfx_z: list[float] = []

    def add(self, view) -> None:
        pitch = view.pitch
        self.pitches += 1
        if view.swing:
            self.swings += 1
            if view.whiff:
                self.whiffs += 1
        else:
            self.takes += 1
        if view.called_strike:
            self.called_strikes += 1
        if view.outside_zone:
            self.out_zone_pitches += 1
            if view.swing:
                self.out_zone_swings += 1
        if view.in_play:
            self.balls_in_play += 1
            speed = _f(pitch.launch_speed)
            angle = _f(pitch.launch_angle)
            woba = _f(pitch.estimated_woba)
            if speed is not None:
                self.exit_speeds.append(speed)
            if angle is not None:
                self.launch_angles.append(angle)
            if woba is not None:
                self.wobas.append(woba)
            if view.hard_hit:
                self.hard_hits += 1
            if view.barrel:
                self.barrels += 1
            if event_is_hit(pitch.event):
                self.hits += 1
            if (pitch.event or "") == "home_run":
                self.home_runs += 1
        speed = _f(pitch.release_speed)
        spin = _f(pitch.release_spin_rate)
        x = _f(pitch.pfx_x)
        z = _f(pitch.pfx_z)
        if speed is not None:
            self.speeds.append(speed)
        if spin is not None:
            self.spins.append(spin)
        if x is not None:
            self.pfx_x.append(x)
        if z is not None:
            self.pfx_z.append(z)

    # ---------------------------------------------------------------- roles

    def batter_stats(self) -> dict:
        contacts = self.swings - self.whiffs
        return {
            "swings": self.swings,
            "takes": self.takes,
            "whiffs": self.whiffs,
            "contacts": contacts,
            "balls_in_play": self.balls_in_play,
            "hits": self.hits,
            "home_runs": self.home_runs,
            "contact_rate": rate(contacts, self.swings),
            "whiff_rate": rate(self.whiffs, self.swings),
            "hard_hit_rate": rate(self.hard_hits, self.balls_in_play),
            "barrel_rate": rate(self.barrels, self.balls_in_play),
            "avg": self._batter_avg(),
            "slg": self._batter_slg(),
            "woba": _avg(self.wobas),
            "xwoba": _avg(self.wobas),
        }

    def pitcher_stats(self) -> dict:
        return {
            "swings": self.swings,
            "takes": self.takes,
            "whiffs": self.whiffs,
            "called_strikes": self.called_strikes,
            "balls_in_play": self.balls_in_play,
            "woba_allowed": _avg(self.wobas),
            "xwoba_allowed": _avg(self.wobas),
            "whiff_rate": rate(self.whiffs, self.swings),
            "called_strike_rate": rate(self.called_strikes, self.pitches),
            "hard_hit_rate_allowed": rate(self.hard_hits, self.balls_in_play),
            "barrel_rate_allowed": rate(self.barrels, self.balls_in_play),
        }

    def arsenal_stats(self) -> dict:
        contacts = self.swings - self.whiffs
        return {
            "usage_rate": None,  # se calcula en arsenal.py con el total global
            "avg_velocity": round(_avg(self.speeds), 2) if self.speeds else None,
            "max_velocity": round(max(self.speeds), 2) if self.speeds else None,
            "avg_spin_rate": round(_avg(self.spins), 2) if self.spins else None,
            "avg_horizontal_break": round(_avg(self.pfx_x), 4) if self.pfx_x else None,
            "avg_vertical_break": round(_avg(self.pfx_z), 4) if self.pfx_z else None,
            "swings": self.swings,
            "whiffs": self.whiffs,
            "called_strikes": self.called_strikes,
            "balls_in_play": self.balls_in_play,
            "whiff_rate": rate(self.whiffs, self.swings),
            "called_strike_rate": rate(self.called_strikes, self.pitches),
            "chase_rate": rate(self.out_zone_swings, self.out_zone_pitches),
            "woba_allowed": _avg(self.wobas),
            "xwoba_allowed": _avg(self.wobas),
            "hard_hit_rate_allowed": rate(self.hard_hits, self.balls_in_play),
            "barrel_rate_allowed": rate(self.barrels, self.balls_in_play),
        }

    # ------------------------------------------------------------- helpers

    def _batter_avg(self) -> Optional[float]:
        # AVG por celda en V1 usa balls_in_play como denominador representativo.
        if self.balls_in_play <= 0:
            return None
        return round(self.hits / self.balls_in_play, 5)

    def _batter_slg(self) -> Optional[float]:
        if self.balls_in_play <= 0:
            return None
        tb = (self.hits - self.home_runs) + 2 * self.home_runs
        return round(tb / self.balls_in_play, 5)