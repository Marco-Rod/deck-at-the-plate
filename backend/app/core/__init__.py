"""
Paquete: app.core
==================
Núcleo de dominio del motor. Reúne los contratos tipados (enums y DTOs) que
usan los módulos puros de `app.engine`. Este paquete NO debe importar
FastAPI, SQLAlchemy ni el paquete `app.models`: permanece agnóstico a la
infraestructura para respetar la Inversión de Dependencias (D en SOLID).

Contenido previsto:
    - enums:         Vocabulario canónico del juego (eventos, posiciones, etc.)
    - engine_types:  DTOs (TypedDict/NamedTuple) que describen los datos que
                     entran y salen del motor de simulación.
"""
from app.core.enums import (
    Difficulty,
    Event,
    GameMode,
    PitchType,
    PlayerRole,
    Position,
    RunnerBase,
    SwingType,
)
from app.core.engine_types import (
    AtBatResult,
    BatterAttrs,
    PitchSelection,
    PitcherAttrs,
    PlayResult,
    Runners,
    SwingSelection,
    TacticsModifiers,
)

__all__ = [
    "Difficulty",
    "Event",
    "GameMode",
    "PitchType",
    "PlayerRole",
    "Position",
    "RunnerBase",
    "SwingType",
    "AtBatResult",
    "BatterAttrs",
    "PitchSelection",
    "PitcherAttrs",
    "PlayResult",
    "Runners",
    "SwingSelection",
    "TacticsModifiers",
]