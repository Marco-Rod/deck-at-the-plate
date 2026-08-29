"""
Vocabulario canónico del juego
================================
Enums que centralizan los strings mágicos usados por el motor (eventos,
posiciones, dificultad, tipos de picheo, etc.). Al derivar de ``str`` los
valores siguen siendo intercambiables con los literales existentes en la base
de datos y en los payloads de la API, por lo que su introducción es 100%
compatible con el código actual.

Beneficios SOLID:
    - Open/Closed: agregar un nuevo evento/picheo es definir una constante,
      no editar cadenas comparadas en N archivos.
    - Elimina typos en runtime: un valor inválido falla en la definición del
      enum, no en mitad de una comparación de strings.
"""

import enum


class Event(str, enum.Enum):
    """Eventos que el motor puede producir en una jugada."""

    STRIKE_SWINGING = "STRIKE_SWINGING"
    STRIKE_LOOKING = "STRIKE_LOOKING"
    STRIKEOUT = "STRIKEOUT"
    BALL = "BALL"
    FOUL = "FOUL"
    WALK = "WALK"
    HIT_1B = "HIT_1B"
    HIT_2B = "HIT_2B"
    HIT_3B = "HIT_3B"
    HOME_RUN = "HOME_RUN"
    OUT_FLY = "OUT_FLY"
    OUT_GROUND = "OUT_GROUND"
    DOUBLE_PLAY = "DOUBLE_PLAY"
    GAME_OVER = "GAME_OVER"

    # --- Clasificaciones auxiliares ---

    @property
    def is_hit(self) -> bool:
        return self in (Event.HIT_1B, Event.HIT_2B, Event.HIT_3B, Event.HOME_RUN)

    @property
    def is_swing_strike(self) -> bool:
        return self in (Event.STRIKE_SWINGING, Event.STRIKE_LOOKING)

    @property
    def is_out_event(self) -> bool:
        """Eventos que registran al menos un out de forma directa."""
        return self in (
            Event.STRIKEOUT,
            Event.OUT_FLY,
            Event.OUT_GROUND,
            Event.DOUBLE_PLAY,
        )


class PitchType(str, enum.Enum):
    """Tipos de picheo soportados por el repertorio de los lanzadores."""

    FOUR_SEAM = "4-SEAM"
    SLIDER = "SLIDER"
    CHANGE = "CHANGE"
    CURVE = "CURVE"
    SINKER = "SINKER"
    CUTTER = "CUTTER"
    IBB = "IBB"  # Base por bolas intencional


class SwingType(str, enum.Enum):
    """Tipos de swing que puede seleccionar el bateador."""

    NORMAL = "NORMAL"
    POWER = "POWER"
    TAKE = "TAKE"
    BUNT = "BUNT"


class Difficulty(str, enum.Enum):
    """Dificultad del rival CPU en modo PvE."""

    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class GameMode(str, enum.Enum):
    """Modo de partida."""

    PVE = "PVE"
    PVP = "PVP"


class PlayerRole(str, enum.Enum):
    """Rol que toma una acción dentro del at-bat."""

    PITCHER = "PITCHER"
    BATTER = "BATTER"


class RunnerBase(str, enum.Enum):
    """Claves del mapa de corredores en state_data ("1b", "2b", "3b")."""

    FIRST = "1b"
    SECOND = "2b"
    THIRD = "3b"


class Position(str, enum.Enum):
    """Posiciones de los jugadores en el diamante."""

    PITCHER = "P"
    STARTER = "SP"
    RELIEVER = "RP"
    CLOSER = "CP"
    TWO_WAY = "TWP"
    CATCHER = "C"
    FIRST_BASE = "1B"
    SECOND_BASE = "2B"
    THIRD_BASE = "3B"
    SHORTSTOP = "SS"
    LEFT_FIELD = "LF"
    CENTER_FIELD = "CF"
    RIGHT_FIELD = "RF"
    DESIGNATED_HITTER = "DH"

    @property
    def is_pitcher(self) -> bool:
        return self in (Position.STARTER, Position.RELIEVER, Position.CLOSER, Position.TWO_WAY)

    @property
    def is_fielder(self) -> bool:
        return self in (
            Position.CATCHER,
            Position.FIRST_BASE,
            Position.SECOND_BASE,
            Position.THIRD_BASE,
            Position.SHORTSTOP,
            Position.LEFT_FIELD,
            Position.CENTER_FIELD,
            Position.RIGHT_FIELD,
            Position.DESIGNATED_HITTER,
        )