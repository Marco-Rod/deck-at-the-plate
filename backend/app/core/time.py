"""Utilidades de tiempo con zona horaria explícita.

Fuente única de timestamps aware en los modelos. Evita ``datetime.utcnow()``
naive, que se interpreta como UTC sin marcarlo como tal.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timestamp actual aware a UTC.

    Postgres lo persiste con tz (timestamp with time zone) y sqlite lo
    serializa sin perder la marca de zona. Testable con monkeypatch.
    """
    return datetime.now(timezone.utc)