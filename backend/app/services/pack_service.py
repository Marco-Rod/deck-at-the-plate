import random
import logging
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import CardRarity, PlayerCardModel, UserLineup
from app.core.enums import PITCHER_POSITIONS
from app.engine.starter_pack import select_starter_cards
from app.engine.lineup_builder import build_optimal_lineup
from app.repositories import (
    add_inventory_item,
    find_cards_by_rarity,
    find_cards_by_team,
    find_cards_excluding_team,
    find_any_card,
    find_inventory_entry,
    get_active_lineup,
    get_or_create_wallet,
    get_user_by_id,
    get_wallet_by_user_id,
)

logger = logging.getLogger(__name__)


class StarterPackConfig:
    """Configuración centralizada del starter pack (13 cartas)."""

    # Posiciones requeridas del baseball (campo + DH)
    REQUIRED_POSITIONS = {"P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"}

    # Clasificación de posiciones (la regla "es pitcher" es global y vive en core)
    PITCHER_POSITIONS = PITCHER_POSITIONS
    FIELDER_POSITIONS = {"C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"}

    # Totales
    FAVORITE_TEAM_CARDS = 7  # Cartas del equipo favorito
    OTHER_TEAMS_CARDS = 6    # Cartas de otros equipos
    TOTAL_CARDS = 13         # Total del pack

    # Orden de rareza (de mayor a menor)
    TIER_PRIORITY = ["DIAMOND", "GOLD", "SILVER", "BRONZE", "COMMON"]


class PackService:
    """Servicio para gestionar starter packs (mazo inicial de 13 cartas)."""

    # Probabilidades de obtención por tipo de sobre (Drop Rates)
    PACK_RATES = {
        "BRONZE": {
            "price": 500,
            "cards_count": 3,
            "rates": {CardRarity.COMMON: 0.60, CardRarity.BRONZE: 0.35, CardRarity.SILVER: 0.05}
        },
        "GOLD": {
            "price": 1500,
            "cards_count": 4,
            "rates": {CardRarity.BRONZE: 0.20, CardRarity.SILVER: 0.50, CardRarity.GOLD: 0.25, CardRarity.DIAMOND: 0.05}
        },
        "DIAMOND": {
            "price": 4000,
            "cards_count": 5,
            "rates": {CardRarity.SILVER: 0.10, CardRarity.GOLD: 0.60, CardRarity.DIAMOND: 0.30}
        }
    }

    @staticmethod
    def _get_missing_positions(selected_cards: List[PlayerCardModel]) -> List[str]:
        """
        Identifica qué posiciones del campo aún no están cubiertas.

        Args:
            selected_cards: Cartas ya seleccionadas

        Returns:
            Lista de posiciones faltantes
            Ej: ['3B', 'SS', 'RF']
        """
        covered_positions = {}
        for card in selected_cards:
            pos = card.position
            if pos != "P":  # "P" se maneja como lanzador genérico
                covered_positions[pos] = covered_positions.get(pos, 0) + 1

        missing = []
        for pos in StarterPackConfig.REQUIRED_POSITIONS:
            if pos != "P" and covered_positions.get(pos, 0) == 0:
                missing.append(pos)

        return missing

    @classmethod
    def assign_starter_pack(cls, db: Session, user_id: str, team_id: str) -> List[PlayerCardModel]:
        """
        Asigna un mazo inicial de 13 cartas al usuario.

        La selección de cartas vive en la capa pura ``app.engine.starter_pack``;
        este servicio solo orquesta lectura de datos, persistencia y transacción.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            team_id: ID del equipo favorito elegido

        Returns:
            Lista de 13 cartas asignadas al usuario
        """
        team_id = team_id.upper()

        # ── PASO 1: Obtener usuario y validar ─────────────────────────────
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Asignar favorite_team_id si no existe
        if not user.favorite_team_id:
            user.favorite_team_id = team_id

        # ── PASO 2: Obtener cartas del equipo favorito ────────────────────
        team_cards = find_cards_by_team(db, team_id)
        if not team_cards:
            raise HTTPException(status_code=500, detail=f"No hay cartas disponibles para {team_id}")

        other_team_cards = find_cards_excluding_team(db, team_id)

        # ── PASO 3-8: Seleccionar las 13 cartas (lógica pura) ─────────────
        logger.info("[ASSIGN_STARTER_PACK] %s cartas equipo %s, %s de otros equipos",
                    len(team_cards), team_id, len(other_team_cards))
        selected_cards = select_starter_cards(team_cards, other_team_cards)

        # ── PASO 9: Guardar cartas en inventario ──────────────────────────
        for card in selected_cards:
            if not find_inventory_entry(db, user_id, card.id):
                add_inventory_item(db, user_id, card.id)

        # ── PASO 9.5: Generar y persistir el lineup ideal inicial ─────────
        # Asegura que el jugador tenga un lineup válido desde el primer día.
        if not get_active_lineup(db, user_id):
            slots = build_optimal_lineup(selected_cards)
            if slots:
                db.add(UserLineup(
                    user_id=user_id,
                    name="Lineup Principal",
                    is_active=True,
                    slots=slots,
                ))

        # ── PASO 10: Actualizar estado usuario ────────────────────────────
        user.has_completed_onboarding = True

        # ── PASO 11: Inicializar cartera (si falta) ───────────────────────
        get_or_create_wallet(db, user_id)

        # ── Commit único de la operación ───────────────────────────────────
        db.commit()

        logger.info("[ASSIGN_STARTER_PACK] FIN - %s cartas asignadas a %s", len(selected_cards), user_id)
        return selected_cards

    @classmethod
    def open_pack(cls, db: Session, user_id: str, pack_type: str) -> List[PlayerCardModel]:
        """
        Abre un sobre de cartas usando stamps del usuario.

        Verifica saldo → cobra cost → genera cartas según drop rates → guarda en inventario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            pack_type: Tipo de sobre ("BRONZE", "GOLD", "DIAMOND")

        Returns:
            Lista de cartas obtenidas
        """
        pack_type = pack_type.upper()
        if pack_type not in cls.PACK_RATES:
            raise HTTPException(status_code=400, detail="Tipo de sobre no válido")

        pack_info = cls.PACK_RATES[pack_type]

        # Verificar saldo de stamps
        wallet = get_wallet_by_user_id(db, user_id)
        if not wallet or wallet.stamps < pack_info["price"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Stamps insuficientes. Requieres {pack_info['price']} stamps."
            )

        # Deducir costo
        wallet.stamps -= pack_info["price"]

        # Generar cartas según drop rates
        pulled_cards = []
        rarities = list(pack_info["rates"].keys())
        probabilities = list(pack_info["rates"].values())

        for _ in range(pack_info["cards_count"]):
            # Seleccionar rareza ponderada por probabilidad
            selected_rarity = random.choices(rarities, weights=probabilities, k=1)[0]

            # Buscar cartas de esa rareza en BD
            matching_cards = find_cards_by_rarity(db, selected_rarity)

            if matching_cards:
                drawn_card = random.choice(matching_cards)
            else:
                # Fallback: si no hay cartas de esa rareza, tomar cualquiera
                drawn_card = find_any_card(db)

            if drawn_card:
                # Guardar en inventario
                add_inventory_item(db, user_id, drawn_card.id)
                pulled_cards.append(drawn_card)

        db.commit()
        return pulled_cards