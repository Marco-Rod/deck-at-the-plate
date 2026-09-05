"""
DTOs del motor
=================
Describe la forma de los datos que entran y salen del motor de simulación.
Reemplaza el acoplamiento a diccionarios sin forma (``dict`` "Sueltos") por
contratos explícitos que los módulos puros pueden consumir sin conocer la base
de datos ni el framework web.

Reglas:
    - Un TypedDict describe la MISMA forma que el código actual ya produce,
      por lo que es comprobable en runtime con ``typing.cast``/mypy sin exigir
      cambios de comportamiento.
    - Todo tipo aquí es agnóstico a la infraestructura (sin SQLAlchemy/FastAPI).
"""

from typing import NamedTuple, NotRequired, Optional, TypedDict


class PitcherAttrs(TypedDict):
    """Atributos de lanzamiento. Claves en español (idioma del engine)."""

    velocidad: int
    control: int
    movimiento: int


class BatterAttrs(TypedDict):
    """Atributos de bateo.

    Visión/clutch son columnas persistidas (NOT NULL post-backfill). Vision
    viene de seeds/backfill_cards.py; el Matchup Engine V1 consumirá clutch.
    """

    contacto: int
    poder: int
    vision: int
    clutch: int


class TacticsModifiers(TypedDict, total=False):
    """Modificadores numéricos aplicados por cartas tácticas activas.

    Todos son factores multiplicativos con valor por defecto 1.0.
    """

    batter_con: float
    batter_pwr: float
    batter_vis: float
    pitcher_mov: float
    pitcher_vel: float
    pitcher_ctl: float


Runners = TypedDict(
    "Runners",
    {
        "1b": Optional[str],
        "2b": Optional[str],
        "3b": Optional[str],
    },
)


class PitchSelection(TypedDict):
    """Selección secreta del lanzador guardada en ``state_data.current_pitch``.

    ``velocity/control/movement`` son opcionales: solo se enriquecen a partir
    del repertorio de la carta justo antes de resolver la jugada.
    """

    pitch_type: str
    zone: int
    velocity: NotRequired[int]
    control: NotRequired[int]
    movement: NotRequired[int]


class SwingSelection(TypedDict):
    """Decisión ofensiva del bateador."""

    swing_type: str
    guessed_zone: Optional[int]
    guessed_pitch: Optional[str]


class PlayResult(NamedTuple):
    """Resultado instantáneo de un duelo calculado por el motor."""

    event: str
    description: str


class AtBatResult(NamedTuple):
    """Resultado integral del procesamiento de una jugada sobre el estado."""

    at_bat_ended: bool
    inning_ended: bool
    final_event: str
    description: str