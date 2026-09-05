"""
Repositorio de telemetría pitch-by-pitch (PitchEventLog)
========================================================
Persiste el payload ya validado por ``services.pitch_telemetry``. El builder y
el repo están separados (SRP): el primero es puro y testeable sin DB; este
solo se encarga de la escritura.

Pauta: los repos NO lanzan HTTPException; solo acceden a datos. El commit lo
hace el caller (misma transacción que la resolución de la jugada).
"""

from app.models import PitchEventLog


def record_pitch_event(db, payload: dict) -> PitchEventLog:
    """Crea y hace flush de un PitchEventLog a partir de un payload válido.

    ``db.flush()`` genera el id y evidencia errores (PK/FK/CHECK) dentro de la
    transacción del juego, sin commitear por su cuenta.
    """
    log = PitchEventLog(**payload)
    db.add(log)
    db.flush()
    return log


def get_pitch_logs_by_game(db, game_id: str, limit: int = 200):
    """Logs de un juego en orden de pitch (para replay/balance)."""
    return (
        db.query(PitchEventLog)
        .filter(PitchEventLog.game_id == game_id)
        .order_by(PitchEventLog.plate_appearance_id, PitchEventLog.pitch_number)
        .limit(limit)
        .all()
    )