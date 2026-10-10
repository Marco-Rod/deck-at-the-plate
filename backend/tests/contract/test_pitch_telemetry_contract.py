"""Contrato de telemetría runtime P5-A (RUNTIME TELEMETRY).

Verifica sobre la API real (SQLite) que resolver un swing:
  * escribe exactamente un ``PitchEventLog`` honesto por pitch resuelto,
  * mantiene una identidad de plate-appearance estable dentro del PA y nueva
    entre PAs,
  * numera los pitches del PA de forma contigua desde 1,
  * sella el ``GameEventLog`` terminal con su PA id, el build del engine y un
    ``sequence_no`` contiguo.
"""

from __future__ import annotations

from app.core.enums import PitchFamily
from app.engine.build import ENGINE_BUILD
from app.models import GameEventLog, PitchEventLog


def _bottom_state(ctx):
    """State_data de la media Baja (el humano HOME batea)."""
    lineup = ctx["roster"]["lineup"]
    return {
        "current_pitch": None,
        "active_batter": lineup[0],
        "home_batter_index": 0,
        "runners": {"1b": None, "2b": None, "3b": None},
        "active_tactics": {"home": None, "away": None},
    }


def _swing(client, game_id, headers, **kwargs):
    payload = {"swing_type": "NORMAL", "guessed_zone": 5}
    payload.update(kwargs)
    return client.post(f"/api/v1/games/{game_id}/swing", json=payload, headers=headers)


def _pitch_logs(seed_session, game_id):
    seed_session.expire_all()
    return (
        seed_session.query(PitchEventLog)
        .filter(PitchEventLog.game_id == game_id)
        .order_by(PitchEventLog.plate_appearance_id, PitchEventLog.pitch_number)
        .all()
    )


def _game_events(seed_session, game_id):
    seed_session.expire_all()
    return (
        seed_session.query(GameEventLog)
        .filter(GameEventLog.game_id == game_id)
        .order_by(GameEventLog.sequence_no)
        .all()
    )


def test_un_swing_registra_un_pitch_log_honesto(
    client, game_factory, mutate_game, seed_session
):
    ctx = game_factory()
    mutate_game(
        ctx["game_id"], columns={"is_top_inning": False}, state=_bottom_state(ctx)
    )

    resp = _swing(client, ctx["game_id"], ctx["headers"])
    assert resp.status_code == 200, resp.text

    logs = _pitch_logs(seed_session, ctx["game_id"])
    assert len(logs) == 1
    log = logs[0]

    assert log.plate_appearance_id
    assert log.pitch_number == 1
    assert log.engine_version == ENGINE_BUILD
    assert 1 <= log.pitcher_zone_choice <= 9
    assert log.pitch_type
    assert log.pitch_family in set(PitchFamily)
    assert abs(sum(log.probability_distribution.values()) - 1.0) < 0.01
    assert 0 <= log.balls_before <= 3
    assert 0 <= log.strikes_before <= 2
    assert 0 <= log.outs_before <= 2
    assert log.result
    assert isinstance(log.zone_match, bool)
    # NORMAL → approach REACT: no hay acierto binario que registrar.
    assert log.approach_match is None


def test_identidad_pa_secuencia_y_versionado(
    client, game_factory, mutate_game, seed_session
):
    ctx = game_factory()
    gid = ctx["game_id"]
    mutate_game(gid, columns={"is_top_inning": False}, state=_bottom_state(ctx))

    # Swings hasta cerrar 2 plate appearances (cap defensivo anti-flake).
    for _ in range(60):
        before = len(_game_events(seed_session, gid))
        resp = _swing(client, gid, ctx["headers"])
        assert resp.status_code == 200, resp.text
        after = len(_game_events(seed_session, gid))
        if after >= 2:
            break

    events = _game_events(seed_session, gid)
    assert len(events) >= 2

    logs = _pitch_logs(seed_session, gid)
    assert logs

    # Agrupar por PA: numeración contigua desde 1.
    by_pa: dict[str, list[int]] = {}
    for log in logs:
        by_pa.setdefault(log.plate_appearance_id, []).append(log.pitch_number)
    assert len(by_pa) >= 2
    for pitch_numbers in by_pa.values():
        assert pitch_numbers == list(range(1, len(pitch_numbers) + 1))

    # GameEventLog terminal: sellado, versionado y con sequence_no contiguo.
    assert [e.sequence_no for e in events] == list(range(1, len(events) + 1))
    for event in events:
        assert event.engine_version == ENGINE_BUILD
        assert event.plate_appearance_id in by_pa
        # Cada pitch log del PA quedó sellado con la misma identidad.
        pa_logs = [log for log in logs if log.plate_appearance_id == event.plate_appearance_id]
        assert pa_logs, "todo PA terminado tiene al menos un pitch log"
        assert all(log.pitch_number >= 1 for log in pa_logs)
