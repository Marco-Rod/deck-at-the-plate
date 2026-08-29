"""
Servicio de aplicacion: sesiones de juego
==========================================
Centraliza la creacion e inicializacion de una sesion 1v1 (el orquestador
aplicativo que antes vivia en ``routers/games.py``). El router queda con la
capa HTTP (auth y mapeo de errores); este modulo con las reglas de dominio y
la persistencia.

Pauta: los servicios pueden lanzar HTTPException (frontera HTTP del handler);
los repos no.
"""

import uuid
import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import GameSession
from app.schemas import CreateGameRequest
from app.engine.deck_manager import initialize_tactics_state
from app.repositories import (
    find_all_cards,
    find_cards_by_team,
    get_active_lineup,
    get_team_by_id,
)

logger = logging.getLogger(__name__)

# Mazos de tacticas predeterminados por defecto
DEFAULT_TACTICS_DECK = ["t1", "t2", "t3", "t4", "t1"]


class GameSessionService:
    """Operaciones aplicativas sobre sesiones de juego."""

    @staticmethod
    def create(db: Session, payload: CreateGameRequest) -> GameSession:
        """
        Crea una nueva sesion de juego 1v1 e inicializa:
        - Marcador 0-0, Inning 1 Alta.
        - Lineups de 9 bateadores por equipo.
        - Mazos tacticos mezclados con mano inicial de 3 cartas.
        - Pitcher activo inicial (el local lanza en la Alta del primer inning).

        En modo PVE el equipo visitante es la CPU.

        Nota: la autorizacion (el humano de la partida debe ser el usuario del
        token) se valida en el router antes de llamar a este servicio.
        """
        # MAPEO: Determinar posiciones basadas en player_position
        if payload.player_position == "AWAY":
            # Usuario elige ser visitante -> CPU es local
            home_user_id = "CPU_BOT"
            away_user_id = payload.home_user_id
            rival_team_id = payload.away_user_id  # Equipo CPU
        elif payload.player_position == "HOME":
            # Usuario elige ser local (comportamiento actual)
            home_user_id = payload.home_user_id
            away_user_id = "CPU_BOT"
            rival_team_id = payload.away_user_id  # Equipo CPU
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="player_position debe ser 'HOME' o 'AWAY'"
            )

        # 1. Obtener lineup del jugador humano
        human_user_id = payload.home_user_id  # El usuario humano siempre viene en home_user_id
        human_is_home = (payload.player_position == "HOME")

        # Inicializar variables
        home_lineup_ids = []
        away_lineup_ids = []
        home_pitcher_id = None
        away_pitcher_id = None

        # Determinar lineup y pitcher del usuario humano segun su posicion
        if human_is_home:
            home_lineup_ids = payload.home_lineup or []
            home_pitcher_id = payload.home_pitcher_id
        else:
            away_lineup_ids = payload.away_lineup or []
            away_pitcher_id = payload.away_pitcher_id

        # Si no viene provisto, buscar del usuario
        if (human_is_home and (not home_lineup_ids or len(home_lineup_ids) < 9)) or \
           (not human_is_home and (not away_lineup_ids or len(away_lineup_ids) < 9)):
            user_lineup = get_active_lineup(db, human_user_id)
            if user_lineup and user_lineup.slots:
                # Normalizar slots: se acepta tanto el objeto completo de la carta
                # ({"id": "card_xxx", ...}) como un id plano ("card_xxx"). Esto hace
                # la carga robusta ante cualquier formato previamente persistido.
                lineup_cards = []
                pitcher_card = None
                for slot, card in user_lineup.slots.items():
                    card_id = (
                        card.get("id")
                        if isinstance(card, dict) and isinstance(card.get("id"), str)
                        else card if isinstance(card, str) else None
                    )
                    if not card_id:
                        continue
                    if slot == "P":
                        pitcher_card = card_id
                    else:
                        lineup_cards.append(card_id)
                lineup_cards = lineup_cards[:9]

                if human_is_home:
                    home_lineup_ids = lineup_cards
                    home_pitcher_id = pitcher_card
                else:
                    away_lineup_ids = lineup_cards
                    away_pitcher_id = pitcher_card

        # 2. Obtener datos de CPU (equipo rival)
        cpu_cards = find_cards_by_team(db, rival_team_id)

        # Cargar nombre completo del equipo rival desde la tabla Team
        rival_team_obj = get_team_by_id(db, rival_team_id)
        rival_team_name = rival_team_obj.name if rival_team_obj else rival_team_id

        # FALLBACK: Si no hay cartas del equipo rival, usar cartas de cualquier equipo
        if not cpu_cards:
            logger.warning("No hay cartas para equipo %s; usando cartas de cualquier equipo.", rival_team_id)
            cpu_cards = find_all_cards(db)

        if not cpu_cards:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No hay cartas disponibles en la base de datos. Ejecuta el seed primero."
            )

        # La regla "es pitcher" vive en PlayerCardModel.is_pitcher / core.PITCHER_POSITIONS
        pitchers = [c for c in cpu_cards if c.is_pitcher]
        batters = [c for c in cpu_cards if c.is_batter]

        # Asignar cartas CPU segun su posicion
        if human_is_home:
            # CPU es visitante (away)
            if not away_pitcher_id and pitchers:
                away_pitcher_id = pitchers[0].id
            if (not away_lineup_ids or len(away_lineup_ids) < 9) and batters:
                away_lineup_ids = [c.id for c in batters[:9]]
                while len(away_lineup_ids) < 9 and cpu_cards:
                    away_lineup_ids.append(cpu_cards[0].id)
        else:
            # CPU es local (home)
            if not home_pitcher_id and pitchers:
                home_pitcher_id = pitchers[0].id
            if (not home_lineup_ids or len(home_lineup_ids) < 9) and batters:
                home_lineup_ids = [c.id for c in batters[:9]]
                while len(home_lineup_ids) < 9 and cpu_cards:
                    home_lineup_ids.append(cpu_cards[0].id)

        # Validaciones de seguridad
        if not home_pitcher_id or not away_pitcher_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Se requiere un lanzador valido para ambos equipos. home={home_pitcher_id}, away={away_pitcher_id}"
            )

        home_tactics = payload.home_tactics_deck or DEFAULT_TACTICS_DECK
        away_tactics = payload.away_tactics_deck or DEFAULT_TACTICS_DECK

        tactics_state = initialize_tactics_state(home_tactics, away_tactics)

        total_innings = payload.total_innings if payload.total_innings in (3, 6, 9) else 9

        game = GameSession(
            id=f"game_{uuid.uuid4().hex[:8]}",
            home_user_id=home_user_id,
            away_user_id=away_user_id,
            state_data={
                "mode": payload.game_mode,
                "difficulty": payload.difficulty,
                "total_innings": total_innings,
                "home_lineup": home_lineup_ids,
                "away_lineup": away_lineup_ids,
                "home_batter_index": 0,
                "away_batter_index": 0,
                "tactics": tactics_state,
                "active_pitcher": home_pitcher_id,  # El local (home) lanza en la Alta
                "active_batter": away_lineup_ids[0] if away_lineup_ids else None,
                "home_pitcher_id": home_pitcher_id,
                "away_pitcher_id": away_pitcher_id,
                "runners": {"1b": None, "2b": None, "3b": None},
                "current_pitch": None,
                "active_tactics": {"home": None, "away": None},
                "pitch_counts": {},
                "last_event": "Juego iniciado",
                "is_game_over": False,
                "rival_team_name": rival_team_name,
                "user_role": payload.player_position,
            }
        )

        db.add(game)
        db.commit()
        db.refresh(game)

        logger.info(
            "Partida creada: %s | modo=%s | dificultad=%s | local=%s | visitante=%s",
            game.id, payload.game_mode, payload.difficulty, home_user_id, away_user_id,
        )

        return game