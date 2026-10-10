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
    """Atributos de lanzamiento. Claves en español (idioma del engine).

    ``stuff`` es SEMÁNTICA (contact-quality suppression, GAMEPLAY-ENGINE-003B):
    el mapper publica aquí el Stuff CRUDO de la carta y ``fatigue_manager``
    sustituye ese valor por el Stuff EFECTIVO ya fatigado. El calculator consume
    el efectivo y nunca ve ``fatigue_factor`` — la transformación de atributos
    físicos es responsabilidad de la capawaters upstream (003B-6A).

    Es ``float`` porque el Stuff efectivo es un producto fraccionario
    (``raw * (1 - 0.50*(1 - factor))``): truncarlo a entero en la frontera
    rompería la reproducción bit-exacta del LAB que exige el contrato S1. El
    Stuff crudo es un entero de carta (0-99), compatible con esta anotación.
    """

    velocidad: int
    control: int
    movimiento: int
    stuff: float


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


class TracedPlay(NamedTuple):
    """Resultado de un duelo junto con el trace de decisiones del engine.

    P5-A (RUNTIME TELEMETRY): envoltura ADITIVA de ``PlayResult``. ``result``
    es exactamente lo que devolvería ``calculate_play_outcome`` (misma
    resolución, mismo orden de draws); ``trace`` describe lo que el engine
    conocía ANTES del RNG decisivo (distribución final por clase de evento,
    draws ejecutados y el draw que realizó el resultado, más el matchup
    efectivo). Nunca se fabrica: sólo expone lo que el motor ya calculó.
    """

    result: PlayResult
    trace: dict


class AtBatResult(NamedTuple):
    """Resultado integral del procesamiento de una jugada sobre el estado."""

    at_bat_ended: bool
    inning_ended: bool
    final_event: str
    description: str