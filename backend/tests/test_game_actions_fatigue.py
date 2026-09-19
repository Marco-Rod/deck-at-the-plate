"""GAMEPLAY-ENGINE-001 — la fatiga calculada debe consumirse en el at-bat.

``resolve_swing`` calcula la fatiga sobre los atributos globales del pitcher
(``apply_pitcher_fatigue``) y luego enriquece ``current_pitch`` con los valores
del repertorio degradados por el factor de fatiga. El contrato:

    fatigue > 0            →  effective < repertoire (por atributo específico)
    fatigue = 0            →  effective == repertoire (por atributo específico)
    pitch identity        →  effective específico ≠ pitcher global fatigado

No compara contra números mágicos: la curva de fatiga puede ajustarse después
(GAMEPLAY-ENGINE-001B) sin tocar esta responsabilidad.
"""

import asyncio
from types import SimpleNamespace

from app.engine import game_actions


class RepertoirePitcher:
    """Pitcher con atributos globales y repertorio observables (stub de carta)."""

    def __init__(self, *, velocity, control, movement, repertoire):
        self.velocity = velocity
        self.control = control
        self.movement = movement
        self.repertoire = repertoire

    def get_pitch_stats(self, pitch_type_name):
        for pitch in self.repertoire or []:
            if pitch["pitch_type"] == pitch_type_name:
                return dict(pitch)
        return None


def _capture_resolve_swing(monkeypatch, pitch_counts):
    """Ejecuta resolve_swing capturando la frontera de calculate_play_outcome.

    Retorna (captured, fresh_ff, pitcher): lo que el calculator recibió, el
    lanzamiento fresco del repertorio y la carta del pitcher.
    """
    fresh_ff = {"pitch_type": "FF", "velocity": 96, "control": 92, "movement": 88}
    pitcher = RepertoirePitcher(
        velocity=90,
        control=88,
        movement=85,
        repertoire=[fresh_ff],
    )
    batter = SimpleNamespace(contact=75, power=75, vision=75, clutch=75)

    captured = {}

    def fake_calculate_play_outcome(
        *,
        pitcher_attrs,
        batter_attrs,
        pitch_selected,
        swing_selected,
        tactics_modifiers=None,
    ):
        captured["pitcher_attrs"] = pitcher_attrs
        captured["pitch_selected"] = pitch_selected
        return ("HIT_1B", "Hit")

    monkeypatch.setattr(game_actions, "calculate_play_outcome", fake_calculate_play_outcome)
    monkeypatch.setattr(
        game_actions,
        "get_card_by_id",
        lambda _db, card_id: pitcher if card_id == "P1" else batter,
    )
    monkeypatch.setattr(
        game_actions,
        "process_at_bat_transition",
        lambda *_args: (False, False, "BALL", "Bola"),
    )
    monkeypatch.setattr(
        game_actions,
        "build_play_resolved_payload",
        lambda *_args, **_kwargs: {"type": "PLAY_RESOLVED"},
    )

    game = SimpleNamespace(
        state_data=None,
        current_inning=1,
        is_top_inning=True,
        balls=0,
        strikes=0,
        outs=0,
        score_home=0,
        score_away=0,
        home_user_id="home-user",
        away_user_id="away-user",
    )
    state = {
        "current_pitch": {"pitch_type": "FF", "zone": 5},
        "pitch_counts": dict(pitch_counts),
        "active_pitcher": "P1",
        "active_batter": "B1",
        "runners": {"1b": None, "2b": None, "3b": None},
        "active_tactics": {},
        "total_innings": 9,
    }

    asyncio.run(
        game_actions.resolve_swing(
            game=game,
            state=state,
            swing_type="NORMAL",
            guessed_zone=None,
            guessed_pitch=None,
            db=object(),
            game_id="game-1",
        )
    )
    return captured, fresh_ff, pitcher


def test_resolve_swing_entrega_repertorio_degradado_por_fatiga(monkeypatch):
    """Con fatiga, el calculator recibe velocidad/control/movimiento específicos degradados."""
    captured, fresh_ff, pitcher = _capture_resolve_swing(
        monkeypatch,
        # 30 -> current_count 31 -> 6 extras sobre threshold 25 (9 innings) -> factor 0.4.
        pitch_counts={"P1": 30},
    )

    selected = captured["pitch_selected"]
    fatigued = captured["pitcher_attrs"]

    # apply_pitcher_fatigue() degradó los atributos globales:
    assert fatigued["velocidad"] < pitcher.velocity
    assert fatigued["control"] < pitcher.control
    assert fatigued["movimiento"] < pitcher.movement

    # …y esa degradación llega ahora al repertorio específico del lanzamiento:
    assert selected["velocity"] < fresh_ff["velocity"]
    assert selected["control"] < fresh_ff["control"]
    assert selected["movement"] < fresh_ff["movement"]

    # El lanzamiento conserva su identidad de repertorio: degradado ≠ global fatigado.
    assert selected["velocity"] != fatigued["velocidad"]


def test_resolve_swing_sin_fatiga_conserva_atributos_del_repertorio(monkeypatch):
    """Sin fatiga (factor 1), el repertorio específico llega intacto al calculator."""
    captured, fresh_ff, _ = _capture_resolve_swing(
        monkeypatch,
        # 10 -> current_count 11, por debajo del threshold -> factor 1.0.
        pitch_counts={"P1": 10},
    )

    selected = captured["pitch_selected"]

    assert selected["velocity"] == fresh_ff["velocity"]
    assert selected["control"] == fresh_ff["control"]
    assert selected["movement"] == fresh_ff["movement"]