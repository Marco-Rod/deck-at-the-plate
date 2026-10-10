"""
Reconciliación P5-C / Paso 7
============================
Dos bloques:

  1. ``reconcile_game`` (verificador puro): ``[]`` cuando el event stream, el
     estado persistido, el box score y el pitch log cuentan la misma historia;
     y detección de cada invariante cuando se inyecta una divergencia.

  2. Regresión del bug GAME_OVER: la jugada que termina el partido debe
     registrarse en ``GameEventLog`` con su tipo real (HOME_RUN/WALK/…), no con
     el envoltorio ``GAME_OVER`` (que sólo pertenece al broadcast).
"""

import asyncio
from types import SimpleNamespace

from app.core.engine_types import PlayResult, TracedPlay
from app.engine import game_actions
from app.services.game_reconciliation import reconcile_game


# ---------------------------------------------------------------------------
# Verificador puro
# ---------------------------------------------------------------------------

def _ev(inning, is_top, runs, seq, event_type, pa_id):
    return SimpleNamespace(
        inning=inning,
        is_top_inning=is_top,
        runs_scored=runs,
        sequence_no=seq,
        event_type=event_type,
        plate_appearance_id=pa_id,
    )


def _pitch(pa_id, number):
    return SimpleNamespace(plate_appearance_id=pa_id, pitch_number=number)


def _consistent_view():
    events = [
        _ev(1, True, 0, 1, "HIT_1B", "pa_a"),
        _ev(1, False, 2, 2, "HOME_RUN", "pa_b"),
        _ev(2, True, 1, 3, "HIT_2B", "pa_c"),
    ]
    # marcador: away (alta) 0+1=1, home (baja) 2
    score_history = {"1_true": 0, "1_false": 2, "2_true": 1}
    box_score = {"batters": {"p1": {"runs": 2}, "p2": {"runs": 1}}}
    pitch_logs = [
        _pitch("pa_a", 1),
        _pitch("pa_b", 1), _pitch("pa_b", 2),
        _pitch("pa_c", 1),
    ]
    return events, score_history, box_score, pitch_logs


def _reconcile(events, score_history, box_score, pitch_logs, **scores):
    score_home = scores.get("score_home", 2)
    score_away = scores.get("score_away", 1)
    return reconcile_game(
        score_home=score_home,
        score_away=score_away,
        score_history=score_history,
        events=events,
        box_score=box_score,
        pitch_logs=pitch_logs,
    )


def test_juego_consistente_no_reporta_issues():
    events, history, box, pitches = _consistent_view()
    assert _reconcile(events, history, box, pitches) == []


def test_detecta_divergencia_marcador_vs_stream():
    events, history, box, pitches = _consistent_view()
    issues = _reconcile(events, history, box, pitches, score_home=3)
    assert "runs.home_state_vs_stream" in {i.code for i in issues}


def test_detecta_divergencia_history_vs_estado():
    events, history, box, pitches = _consistent_view()
    history = {**history, "3_true": 9}
    codes = {i.code for i in _reconcile(events, history, box, pitches, score_home=2, score_away=1)}
    assert "runs.history_vs_state" in codes
    assert "runs.history_per_inning_vs_stream" in codes


def test_detecta_divergencia_box_vs_estado():
    events, history, box, pitches = _consistent_view()
    box = {"batters": {"p1": {"runs": 0}}}  # el stream/estado dicen 3
    codes = {i.code for i in _reconcile(events, history, box, pitches)}
    assert "runs.box_vs_state" in codes


def test_detecta_sequence_no_no_contiguo():
    events, history, box, pitches = _consistent_view()
    events[2].sequence_no = 5
    codes = {i.code for i in _reconcile(events, history, box, pitches)}
    assert "sequence.not_contiguous" in codes


def test_detecta_game_over_en_el_stream():
    events, history, box, pitches = _consistent_view()
    events[1].event_type = "GAME_OVER"
    codes = {i.code for i in _reconcile(events, history, box, pitches)}
    assert "classification.game_over_in_stream" in codes


def test_detecta_pa_sin_pitch_logs():
    events, history, box, pitches = _consistent_view()
    pitches = [p for p in pitches if p.plate_appearance_id != "pa_b"]
    codes = {i.code for i in _reconcile(events, history, box, pitches)}
    assert "pitch.pa_without_pitch_logs" in codes


def test_detecta_pa_no_contiguo():
    events, history, box, pitches = _consistent_view()
    pitches = [_pitch("pa_b", 1), _pitch("pa_b", 3)]  # falta el 2
    codes = {i.code for i in _reconcile(events, history, box, pitches)}
    assert "pitch.pa_not_contiguous" in codes


def test_box_score_y_pitch_logs_son_opcionales():
    events, history, _, _ = _consistent_view()
    assert reconcile_game(
        score_home=2, score_away=1, score_history=history, events=events,
    ) == []


# ---------------------------------------------------------------------------
# Regresión: el play que termina el partido se registra con su tipo real
# ---------------------------------------------------------------------------

class _FakePitcher:
    def get_pitch_stats(self, _pitch_type):
        return None


def test_walk_off_se_registra_como_play_real(monkeypatch, db):
    from app.models import GameEventLog

    pitcher = _FakePitcher()
    batter = SimpleNamespace(id="batter_1", player_id=None)
    game = SimpleNamespace(
        state_data=None, id="game_walkoff",
        current_inning=9, is_top_inning=False,
        balls=0, strikes=0, outs=0, score_home=1, score_away=1,
        home_user_id="home", away_user_id="away",
    )
    state = {
        "current_pitch": {"pitch_type": "4-SEAM", "zone": 5},
        "pitch_counts": {},
        "active_pitcher": "pitcher_1",
        "active_batter": "batter_1",
        "runners": {"1b": None, "2b": None, "3b": None},
        "active_tactics": {},
        "total_innings": 9,
        "home_lineup": [f"H{i}" for i in range(9)],
        "away_lineup": [f"A{i}" for i in range(9)],
        "home_batter_index": 0,
        "away_batter_index": 0,
    }

    monkeypatch.setattr(
        game_actions, "get_card_by_id",
        lambda _db, cid: pitcher if cid == "pitcher_1" else batter,
    )
    monkeypatch.setattr(game_actions, "map_card_to_pitcher_attrs", lambda _c: {})
    monkeypatch.setattr(game_actions, "map_card_to_batter_attrs", lambda _c: {})
    monkeypatch.setattr(game_actions, "apply_pitcher_fatigue", lambda attrs, *_: attrs)
    monkeypatch.setattr(
        game_actions, "calculate_play_outcome_with_trace",
        lambda **_kwargs: TracedPlay(result=PlayResult("HOME_RUN", "¡HOME RUN!"), trace={}),
    )
    monkeypatch.setattr(game_actions, "_record_pitch_telemetry", lambda *a, **k: None)
    monkeypatch.setattr(
        game_actions, "build_play_resolved_payload",
        lambda *_a, **_k: {"type": "PLAY_RESOLVED"},
    )

    event, _description, _inning_ended = asyncio.run(
        game_actions.resolve_swing(
            game=game,
            state=state,
            swing_type="NORMAL",
            guessed_zone=None,
            guessed_pitch=None,
            db=db,
            game_id="game_walkoff",
        )
    )

    # El broadcast sigue recibiendo GAME_OVER (contrato del cliente)…
    assert event == "GAME_OVER"
    # …pero el event stream registra el PLAY real.
    rows = db.query(GameEventLog).filter(GameEventLog.game_id == "game_walkoff").all()
    assert len(rows) == 1
    assert rows[0].event_type == "HOME_RUN"
    assert rows[0].runs_scored == 1
