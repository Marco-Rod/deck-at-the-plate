"""Normalización de zonas (spec sección 14).

Conservamos statcast_zone tal cual y derivamos game_zone solo cuando cae en
1-9 (la retícula del gameplay). Los pitches fuera de la zona de strike se
conservan en RAW para señales de chase/discipline pero no se fuerzan a zona.
"""

from typing import Optional


def game_zone_from_statcast(statcast_zone: Optional[int]) -> Optional[int]:
    if statcast_zone is None:
        return None
    if 1 <= statcast_zone <= 9:
        return int(statcast_zone)
    return None