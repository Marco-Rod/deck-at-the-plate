"""Validación previa a persistencia y a agregación (spec secciones 6 y 48).

Los errores de raw se reportan como rechazos (DataImportRun.rows_rejected), no
como fallos de la ejecución completa.
"""

from etl.validators.analytics import validate_profile
from etl.validators.raw import validate_raw_row

__all__ = ["validate_profile", "validate_raw_row"]