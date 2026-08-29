"""
Repositorio de estadísticas de partida (GameEventLog)
======================================================
Centraliza el registro de eventos y la agregación del box score.
Sustituye al antiguo `engine/stats_recorder.py`: la persistencia vive en la
capa de datos (repositories), no en el motor.

Pauta: los repos NO lanzan HTTPException; solo acceden a datos.
"""

import uuid

from app.core.enums import Event
from app.models import GameEventLog
from app.repositories.card_repository import get_card_by_id


# ---------------------------------------------------------------------------
# Clasificación declarativa de eventos (Open/Closed)
# ---------------------------------------------------------------------------
# Agregar un evento nuevo (p. ej. SACRIFICE_FLY) = añadir su entrada aquí.
# Box score y stats de jugador lo heredan automáticamente: no se editan cadenas.
_BAT_KEYS_BOX: dict[str, tuple[str, ...]] = {
    Event.HIT_1B.value: ("hits", "singles"),
    Event.HIT_2B.value: ("hits", "doubles"),
    Event.HIT_3B.value: ("hits", "triples"),
    Event.HOME_RUN.value: ("hits", "home_runs"),
    Event.STRIKEOUT.value: ("strikeouts",),
    Event.WALK.value: ("walks",),
}

# La vista de jugador no acumula "singles" (compatible con la respuesta legada).
_BAT_KEYS_PLAYER: dict[str, tuple[str, ...]] = {
    Event.HIT_1B.value: ("hits",),
    Event.HIT_2B.value: ("hits", "doubles"),
    Event.HIT_3B.value: ("hits", "triples"),
    Event.HOME_RUN.value: ("hits", "home_runs"),
    Event.STRIKEOUT.value: ("strikeouts",),
    Event.WALK.value: ("walks",),
}

_PITCH_KEYS: dict[str, tuple[str, ...]] = {
    Event.HIT_1B.value: ("hits_allowed",),
    Event.HIT_2B.value: ("hits_allowed",),
    Event.HIT_3B.value: ("hits_allowed",),
    Event.HOME_RUN.value: ("hits_allowed", "home_runs_allowed"),
    Event.STRIKEOUT.value: ("strikeouts",),
    Event.WALK.value: ("walks",),
}


def _event_key(event_type) -> str:
    """Normaliza un evento (str o miembro de Event) a la clave canónica del registro."""
    try:
        return Event(event_type).value
    except (ValueError, TypeError):
        return str(event_type)


def record_game_event(
    db,
    game_id: str,
    event_type: str,
    inning: int,
    is_top_inning: bool,
    batter_id: str,
    pitcher_id: str,
    balls: int = 0,
    strikes: int = 0,
    outs: int = 0,
    runners_on_base: dict = None,
    runs_scored: int = 0,
    rbi: int = 0,
) -> GameEventLog:
    """
    Registra un evento de la partida en la base de datos.

    Args:
        db: Sesión de base de datos
        game_id: ID de la partida
        event_type: Tipo de evento (HIT_1B, HOME_RUN, STRIKEOUT, etc.)
        inning: Número del inning
        is_top_inning: True si es Alta, False si es Baja
        batter_id: ID de la tarjeta del bateador
        pitcher_id: ID de la tarjeta del pitcher
        balls: Conteo de bolas
        strikes: Conteo de strikes
        outs: Outs en la entrada
        runners_on_base: Dict con corredores en base
        runs_scored: Carreras anotadas
        rbi: RBIs generados

    Returns:
        GameEventLog registrado
    """
    batter_card = get_card_by_id(db, batter_id)
    pitcher_card = get_card_by_id(db, pitcher_id)

    batter_name = batter_card.name if batter_card else "Unknown Batter"
    pitcher_name = pitcher_card.name if pitcher_card else "Unknown Pitcher"

    event_log = GameEventLog(
        id=f"event_{uuid.uuid4().hex[:8]}",
        game_id=game_id,
        event_type=event_type,
        inning=inning,
        is_top_inning=is_top_inning,
        batter_id=batter_id,
        pitcher_id=pitcher_id,
        batter_name=batter_name,
        pitcher_name=pitcher_name,
        balls=balls,
        strikes=strikes,
        outs=outs,
        runners_on_base=runners_on_base or {},
        runs_scored=runs_scored,
        rbi=rbi,
    )

    db.add(event_log)
    db.commit()
    db.refresh(event_log)

    return event_log


def get_game_box_score(db, game_id: str) -> dict:
    """
    Calcula el box score (resumen de estadísticas) de una partida.

    Retorna:
    {
        "batters": {
            "player_id": {
                "name": "Player Name",
                "at_bats": 4,
                "hits": 2,
                "doubles": 1,
                "triples": 0,
                "home_runs": 1,
                "rbi": 3,
                "runs": 2,
                "strikeouts": 1,
                "walks": 1,
            },
            ...
        },
        "pitchers": {
            "player_id": {
                "name": "Pitcher Name",
                "strikeouts": 8,
                "walks": 2,
                "hits_allowed": 5,
                "home_runs_allowed": 1,
                "runs_allowed": 3,
            },
            ...
        }
    }
    """
    events = db.query(GameEventLog).filter(GameEventLog.game_id == game_id).all()

    batters = {}
    pitchers = {}

    for event in events:
        evt_key = _event_key(event.event_type)

        # Estadísticas de bateador
        if event.batter_id not in batters:
            batters[event.batter_id] = {
                "name": event.batter_name,
                "at_bats": 0,
                "hits": 0,
                "singles": 0,
                "doubles": 0,
                "triples": 0,
                "home_runs": 0,
                "rbi": 0,
                "runs": 0,
                "strikeouts": 0,
                "walks": 0,
            }

        # Contar at-bats (cualquier evento es un AB excepto walks)
        if evt_key != Event.WALK.value:
            batters[event.batter_id]["at_bats"] += 1

        # Acumular buckets de bateo declarativamente (registry _BAT_KEYS_BOX)
        for key in _BAT_KEYS_BOX.get(evt_key, ()):
            batters[event.batter_id][key] += 1

        # RBIs y carreras
        batters[event.batter_id]["rbi"] += event.rbi
        batters[event.batter_id]["runs"] += event.runs_scored

        # Estadísticas de pitcher
        if event.pitcher_id not in pitchers:
            pitchers[event.pitcher_id] = {
                "name": event.pitcher_name,
                "strikeouts": 0,
                "walks": 0,
                "hits_allowed": 0,
                "home_runs_allowed": 0,
                "runs_allowed": 0,
            }

        # Acumular buckets de pitcher declarativamente (registry _PITCH_KEYS)
        for key in _PITCH_KEYS.get(evt_key, ()):
            pitchers[event.pitcher_id][key] += 1

        pitchers[event.pitcher_id]["runs_allowed"] += event.runs_scored

    return {
        "batters": batters,
        "pitchers": pitchers,
    }


def get_player_game_stats(db, game_id: str, player_id: str) -> dict:
    """
    Obtiene estadísticas de un jugador específico en una partida.
    Puede ser bateador o pitcher.
    """
    events = db.query(GameEventLog).filter(
        (GameEventLog.game_id == game_id) &
        ((GameEventLog.batter_id == player_id) | (GameEventLog.pitcher_id == player_id))
    ).all()

    stats = {
        "batting": {
            "at_bats": 0,
            "hits": 0,
            "doubles": 0,
            "triples": 0,
            "home_runs": 0,
            "rbi": 0,
            "runs": 0,
            "strikeouts": 0,
            "walks": 0,
            "events": [],
        },
        "pitching": {
            "strikeouts": 0,
            "walks": 0,
            "hits_allowed": 0,
            "home_runs_allowed": 0,
            "runs_allowed": 0,
        }
    }

    for event in events:
        evt_key = _event_key(event.event_type)

        if event.batter_id == player_id:
            if evt_key != Event.WALK.value:
                stats["batting"]["at_bats"] += 1

            # Acumular buckets de bateo declarativamente (registry _BAT_KEYS_PLAYER)
            for key in _BAT_KEYS_PLAYER.get(evt_key, ()):
                stats["batting"][key] += 1

            stats["batting"]["rbi"] += event.rbi
            stats["batting"]["runs"] += event.runs_scored
            stats["batting"]["events"].append({
                "inning": event.inning,
                "event": event.event_type,
                "rbi": event.rbi,
            })

        if event.pitcher_id == player_id:
            # Acumular buckets de pitcher declarativamente (registry _PITCH_KEYS)
            for key in _PITCH_KEYS.get(evt_key, ()):
                stats["pitching"][key] += 1

            stats["pitching"]["runs_allowed"] += event.runs_scored

    return stats