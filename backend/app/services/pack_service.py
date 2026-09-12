import random
import logging
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import CardCatalog, CardRarity, PlayerCardModel, UserLineup
from app.core.enums import PITCHER_POSITIONS
from app.engine.starter_pack import select_starter_cards
from app.engine.lineup_builder import build_optimal_lineup
from app.repositories import (
    add_inventory_item,
    find_cards_by_rarity,
    find_cards_by_team,
    find_cards_excluding_team,
    find_inventory_entry,
    get_active_lineup,
    get_active_pack_catalog,
    get_or_create_wallet,
    get_user_by_id,
    get_wallet_by_user_id,
)
from app.repositories.team_repository import resolve_team_to_uuid

logger = logging.getLogger(__name__)


class PackPoolError(HTTPException):
    """Inconsistencia de datos/configuration del pool: nunca degrada silencioso.

    409 porque el catalogo/pool no puede servir la configuracion solicitada y
    la transaccion (y el cobro de stamps) debe abortarse.
    """

    def __init__(self, message: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)


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

        # Resolver abreviatura pública → UUID de la franquicia GAME.
        resolved_team_id = resolve_team_to_uuid(db, team_id)
        if resolved_team_id is None:
            raise HTTPException(status_code=404, detail=f"Equipo no encontrado: {team_id}")

        # Asignar favorite_team_id si no existe
        if not user.favorite_team_id:
            user.favorite_team_id = resolved_team_id

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
    def open_pack(
        cls,
        db: Session,
        user_id: str,
        pack_type: str,
        *,
        season: int | None = None,
        catalog_id: str | None = None,
        edition_type: str = "BASE",
    ) -> List[PlayerCardModel]:
        """
        Abre un sobre de cartas usando stamps del usuario.

        El pool de packs se fija a UN catálogo ACTIVE (nunca a todos los
        ACTIVE del sistema): si no se provee catalog_id, se resuelve la edición
        ACTIVE de la temporada (la más reciente si no hay season). Debe ser
        además del edition_type dado (BASE por defecto). Un tier configurado
        sin pool con cartas elegibles aborta el sobre con PackPoolError ANTES
        de cobrar; jamás cae a legacy/semillas/retirados.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            pack_type: Tipo de sobre ("BRONZE", "GOLD", "DIAMOND")
            season: Temporada del catálogo ACTIVE (opcional)
            catalog_id: Catálogo publicado exacto (opcional)
            edition_type: Tipo de edición de catálogo ("BASE" por defecto)
        """
        pack_type = pack_type.upper()
        if pack_type not in cls.PACK_RATES:
            raise HTTPException(status_code=400, detail="Tipo de sobre no válido")

        pack_info = cls.PACK_RATES[pack_type]

        # ── PASO 1: resolver UN catálogo ACTIVE meta del pool ──────────────
        if catalog_id is not None:
            target = db.get(CardCatalog, catalog_id)
            if target is None or target.status != "ACTIVE":
                raise PackPoolError(f"catálogo no active para packs: {catalog_id}")
            if target.edition_type != edition_type:
                raise PackPoolError(
                    f"catálogo {catalog_id} no es de tipo {edition_type} para packs"
                )
        else:
            target = get_active_pack_catalog(db, season=season, edition_type=edition_type)
        if target is None:
            raise PackPoolError("sin catálogo ACTIVE para abrir sobres")

        # ── PASO 2: pre-validar el pool de este sobre (nunca fallback) ─────
        missing = []
        for rarity in pack_info["rates"]:
            if not find_cards_by_rarity(db, rarity, catalog_id=target.id):
                missing.append(rarity.value)
        if missing:
            raise PackPoolError(
                f"pool sin cartas elegibles para {', '.join(missing)} "
                f"en catálogo {target.id}"
            )

        # ── PASO 3: verificar saldo de stamps ──────────────────────────────
        wallet = get_wallet_by_user_id(db, user_id)
        if not wallet or wallet.stamps < pack_info["price"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Stamps insuficientes. Requieres {pack_info['price']} stamps."
            )

        # Deducir costo
        wallet.stamps -= pack_info["price"]

        # ── PASO 4: generar cartas según drop rates ────────────────────────
        pulled_cards = []
        rarities = list(pack_info["rates"].keys())
        probabilities = list(pack_info["rates"].values())

        for _ in range(pack_info["cards_count"]):
            # Seleccionar rareza ponderada por probabilidad
            selected_rarity = random.choices(rarities, weights=probabilities, k=1)[0]

            # Pool fijo al catálogo ACTIVE resuelto (jamás global).
            matching_cards = find_cards_by_rarity(
                db, selected_rarity, catalog_id=target.id
            )
            if not matching_cards:
                raise PackPoolError(
                    f"pool vacío para {selected_rarity.value} en catálogo {target.id}"
                )
            drawn_card = random.choice(matching_cards)

            # Guardar en inventario
            add_inventory_item(db, user_id, drawn_card.id)
            pulled_cards.append(drawn_card)

        db.commit()
        return pulled_cards