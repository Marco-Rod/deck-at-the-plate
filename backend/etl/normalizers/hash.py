"""Hash canónico del payload raw (spec sección 18).

SHA-256 sobre JSON canónico (sort_keys + separadores compactos). El hash NO
reemplaza la clave natural; sirve para detectar correcciones retroactivas de
Statcast. Los valores se convierten a primitivas antes de hashear.
"""

import hashlib
import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _to_primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_primitive(v) for v in value]
    return value


def canonical_hash(payload: dict) -> str:
    primitive = {k: _to_primitive(v) for k, v in payload.items()}
    canonical = json.dumps(primitive, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_to_hash_payload(record: Any) -> dict:
    """Payload hasheable desde un DTO frozen (spec sección 18: campos relevantes)."""
    return _to_primitive(asdict(record))