"""
Reconciliación de telemetría de partida (P5-C / Paso 7)
=======================================================
Demuestra que las TRES representaciones de una partida cuentan la misma
historia:

    event stream (GameEventLog + PitchEventLog)
        ↔ persisted state (GameSession.score_*, state_data.score_history)
        ↔ box score / stats (agregación declarativa de GameEventLog)

``reconcile_game`` es PURO: no toca la base de datos ni el estado; recibe las
tres vistas ya materializadas y devuelve la lista de divergencias. Un juego
consistente devuelve ``[]``.

Regla del modelo: la reconciliación no "arregla" nada. Sólo reporta. Cualquier
arreglo pertenece a la ruta que produjo el dato (p. ej. clasificar bien el play
terminal, no el agregador).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional, Sequence


@dataclass(frozen=True)
class ReconciliationIssue:
    """Una divergencia entre dos de las tres representaciones."""

    code: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover - conveniencia de logs
        return f"[{self.code}] {self.detail}"


def _event_value(event) -> str:
    """Normaliza un evento (miembro de ``Event`` o string) a su valor canónico."""
    return event.value if hasattr(event, "value") else str(event)


def _inning_key(inning: int, is_top_inning: bool) -> str:
    return f"{inning}_{str(bool(is_top_inning)).lower()}"


def reconcile_game(
    *,
    score_home: int,
    score_away: int,
    score_history: Optional[dict],
    events: Sequence[Any],
    box_score: Optional[dict] = None,
    pitch_logs: Optional[Sequence[Any]] = None,
) -> list[ReconciliationIssue]:
    """Reconcilia event stream ↔ estado persistido ↔ box score ↔ pitch log.

    Args:
        score_home / score_away: marcador persistido (GameSession).
        score_history: ``state_data["score_history"]`` (carreras por media
            entrada), o ``None``/``{}`` si la partida no anotó.
        events: ``GameEventLog`` de la partida (una fila por PA terminado).
        box_score: salida de ``get_game_box_score``; si es ``None`` se omiten
            los checks que dependen del box score.
        pitch_logs: ``PitchEventLog`` de la partida; si es ``None`` se omite el
            check de vinculación PA ↔ pitches.

    Returns:
        Lista de ``ReconciliationIssue``. ``[]`` = las tres vistas concuerdan.
    """
    issues: list[ReconciliationIssue] = []
    score_history = score_history or {}

    # --- event stream ↔ persisted state -----------------------------------
    away_stream = sum(int(e.runs_scored or 0) for e in events if e.is_top_inning)
    home_stream = sum(int(e.runs_scored or 0) for e in events if not e.is_top_inning)

    if away_stream != score_away:
        issues.append(ReconciliationIssue(
            "runs.away_state_vs_stream",
            f"score_away={score_away} pero el stream suma {away_stream}",
        ))
    if home_stream != score_home:
        issues.append(ReconciliationIssue(
            "runs.home_state_vs_stream",
            f"score_home={score_home} pero el stream suma {home_stream}",
        ))

    total_state = score_home + score_away
    history_total = sum(int(v or 0) for v in score_history.values())
    if history_total != total_state:
        issues.append(ReconciliationIssue(
            "runs.history_vs_state",
            f"score_history total={history_total} pero el marcador suma {total_state}",
        ))

    # --- carreras por media entrada: stream ↔ score_history ----------------
    stream_by_inning = Counter()
    for e in events:
        runs = int(e.runs_scored or 0)
        if runs:
            stream_by_inning[_inning_key(e.inning, e.is_top_inning)] += runs
    for key in sorted(set(stream_by_inning) | set(score_history)):
        stream_runs = stream_by_inning.get(key, 0)
        history_runs = int(score_history.get(key, 0) or 0)
        if stream_runs != history_runs:
            issues.append(ReconciliationIssue(
                "runs.history_per_inning_vs_stream",
                f"{key}: stream={stream_runs} vs score_history={history_runs}",
            ))

    # --- box score ↔ estado ------------------------------------------------
    if box_score is not None:
        box_runs = sum(
            int(b.get("runs", 0) or 0) for b in (box_score.get("batters") or {}).values()
        )
        if box_runs != total_state:
            issues.append(ReconciliationIssue(
                "runs.box_vs_state",
                f"box score suma {box_runs} carreras pero el marcador suma {total_state}",
            ))

    # --- orden estructural del stream -------------------------------------
    sequences = sorted(int(e.sequence_no) for e in events if e.sequence_no is not None)
    if sequences:
        expected = list(range(1, len(sequences) + 1))
        if sequences != expected:
            issues.append(ReconciliationIssue(
                "sequence.not_contiguous",
                f"sequence_no del stream={sequences} (se esperaba 1..{len(sequences)})",
            ))

    # --- clasificación: GAME_OVER no es un evento de jugada ----------------
    invalid = [e for e in events if _event_value(e.event_type) == "GAME_OVER"]
    if invalid:
        issues.append(ReconciliationIssue(
            "classification.game_over_in_stream",
            f"{len(invalid)} evento(s) registrados como GAME_OVER (deben ser la jugada real)",
        ))

    # --- pitch log ↔ PA -----------------------------------------------------
    if pitch_logs is not None:
        pitches_by_pa: dict[str, list[int]] = {}
        for log in pitch_logs:
            pitches_by_pa.setdefault(log.plate_appearance_id, []).append(
                int(log.pitch_number)
            )
        for event in events:
            pa_id = event.plate_appearance_id
            if not pa_id:
                continue
            numbers = sorted(pitches_by_pa.get(pa_id, []))
            if not numbers:
                issues.append(ReconciliationIssue(
                    "pitch.pa_without_pitch_logs",
                    f"PA {pa_id} no tiene ningún PitchEventLog",
                ))
            elif numbers != list(range(1, len(numbers) + 1)):
                issues.append(ReconciliationIssue(
                    "pitch.pa_not_contiguous",
                    f"PA {pa_id} pitches={numbers} (se esperaba 1..{len(numbers)})",
                ))

    return issues


def reconcile_game_from_db(db, game) -> list[ReconciliationIssue]:
    """Materializa las tres vistas de ``game`` desde la BD y las reconcilia."""
    from app.models import GameEventLog, PitchEventLog
    from app.repositories import get_game_box_score

    events = (
        db.query(GameEventLog)
        .filter(GameEventLog.game_id == game.id)
        .all()
    )
    pitch_logs = (
        db.query(PitchEventLog)
        .filter(PitchEventLog.game_id == game.id)
        .all()
    )
    box_score = get_game_box_score(db, game.id)
    state_data = game.state_data or {}

    return reconcile_game(
        score_home=game.score_home,
        score_away=game.score_away,
        score_history=state_data.get("score_history"),
        events=events,
        box_score=box_score,
        pitch_logs=pitch_logs,
    )
