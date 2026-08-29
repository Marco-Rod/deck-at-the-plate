import random
import logging
from typing import List, Dict, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import PlayerCardModel, CardRarity, UserWallet, UserCardInventory, User
from app.core.enums import PITCHER_POSITIONS

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
    def _group_cards_by_rarity(cards: List[PlayerCardModel]) -> Dict[str, List[PlayerCardModel]]:
        """
        Agrupa cartas por rareza.
        
        Args:
            cards: Lista de cartas
            
        Returns:
            Diccionario con cartas agrupadas por rareza
            Ej: {"DIAMOND": [...], "GOLD": [...], ...}
        """
        by_rarity = {}
        for card in cards:
            rarity = card.rarity.name if card.rarity else "COMMON"
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            by_rarity[rarity].append(card)
        return by_rarity

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

    @staticmethod
    def assign_starter_pack(db: Session, user_id: str, team_id: str) -> List[PlayerCardModel]:
        """
        Asigna un mazo inicial de 13 cartas al usuario.
        
        LÓGICA SIMPLIFICADA Y CLARA:
        ==============================
        1. EQUIPO FAVORITO (7 cartas):
           - Obtener tier máximo disponible en el equipo (sea DIAMOND, GOLD, SILVER, etc.)
           - Tomar 1 carta del tier máximo
           - Rellenar 6 cartas restantes con tiers inferiores (SILVER → BRONZE → COMMON)
           - Descartando el tier ya usado
        
        2. OTROS EQUIPOS (6 cartas):
           - Filtrar cartas de todos los demás equipos
           - Cubrir posiciones faltantes del sobre
           - Rellenar sin restricción de rareza si es necesario
        
        3. TOTAL: 13 cartas con cobertura de posiciones
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            team_id: ID del equipo favorito elegido
            
        Returns:
            Lista de 13 cartas asignadas al usuario
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"[ASSIGN_STARTER_PACK] INICIO")
        logger.info(f"{'='*80}")
        logger.info(f"[INPUT] user_id={user_id}, team_id={team_id}")
        
        team_id = team_id.upper()
        logger.info(f"[NORMALIZATION] team_id normalizado a: {team_id}")
        
        selected_cards = []
        selected_set = set()
        
        # ========== PASO 1: Obtener usuario y validar ==========
        logger.info(f"\n[PASO 1] Obtener usuario y equipo elegido")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"[ERROR] Usuario {user_id} no encontrado")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Asignar favorite_team_id si no existe
        if not user.favorite_team_id:
            user.favorite_team_id = team_id
            logger.info(f"  [UPDATE] favorite_team_id asignado a: {team_id}")
        else:
            logger.info(f"  [INFO] favorite_team_id ya existe: {user.favorite_team_id}")
        
        # ========== PASO 2: Obtener cartas del equipo favorito ==========
        logger.info(f"\n[PASO 2] Obtener cartas del equipo favorito ({team_id})")
        team_cards = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id == team_id
        ).all()
        
        if not team_cards:
            logger.error(f"[ERROR] No hay cartas disponibles para {team_id}")
            raise HTTPException(status_code=500, detail=f"No hay cartas disponibles para {team_id}")
        
        logger.info(f"  [TOTAL] {len(team_cards)} cartas disponibles en {team_id}")
        
        # ========== PASO 3: Seleccionar 7 cartas del equipo favorito ==========
        logger.info(f"\n[PASO 3] Seleccionar 7 cartas del equipo favorito (1 del tier máximo + 6 de tiers inferiores)")
        logger.info(f"  [CONSTRAINT] Máximo 2 lanzadores (SP) en todo el pack")
        
        # Agrupar cartas por tier
        team_by_tier = {}
        for tier in StarterPackConfig.TIER_PRIORITY:
            team_by_tier[tier] = [c for c in team_cards if c.rarity.name == tier]
        
        # LOG: Mostrar distribución de tiers disponibles en el equipo
        logger.info(f"  [DISTRIBUCION_TIERS_EQUIPO]")
        for tier in StarterPackConfig.TIER_PRIORITY:
            count = len(team_by_tier[tier])
            logger.info(f"    - {tier}: {count} cartas")
        
        # Encontrar el tier MÁXIMO disponible en el equipo
        highest_tier = next((t for t in StarterPackConfig.TIER_PRIORITY if team_by_tier[t]), None)
        if not highest_tier:
            logger.error(f"[ERROR] No se encontraron cartas clasificadas en {team_id}")
            raise HTTPException(status_code=500, detail=f"No hay cartas clasificadas en {team_id}")
        
        logger.info(f"  [TIER_MAXIMO] {highest_tier} ({len(team_by_tier[highest_tier])} cartas disponibles)")
        
        # Tomar 1 carta del tier máximo (sin restricción, podría ser SP)
        top_card = random.choice(team_by_tier[highest_tier])
        selected_team_cards = [top_card]
        selected_set.add(top_card.id)
        sp_count = 1 if top_card.position == "SP" else 0
        logger.info(f"    1. {top_card.name} ({team_id}) - Pos: {top_card.position} - {top_card.rarity.name}")
        
        # Rellenar 6 cartas restantes (1 por cada tier inferior, luego rellenar del último disponible)
        remaining_needed = 6
        cards_added = 1  # Ya tenemos 1 del tier máximo
        highest_idx = StarterPackConfig.TIER_PRIORITY.index(highest_tier)
        
        # Encontrar tiers inferiores disponibles
        lower_tiers = StarterPackConfig.TIER_PRIORITY[highest_idx + 1:]  # Tiers menores
        last_available_tier = None
        
        # FASE 2A: Tomar 1 de cada tier inferior disponible (respetando límite de SP)
        for tier in lower_tiers:
            if remaining_needed <= 0:
                break
            
            available = [c for c in team_by_tier[tier] if c.id not in selected_set]
            
            # Si ya tenemos 2 SP, filtrar
            if sp_count >= 2:
                available = [c for c in available if c.position != "SP"]
            
            if available:
                card = random.choice(available)
                selected_team_cards.append(card)
                selected_set.add(card.id)
                if card.position == "SP":
                    sp_count += 1
                remaining_needed -= 1
                last_available_tier = tier
                logger.info(f"    {cards_added + 1}. {card.name} ({team_id}) - Pos: {card.position} - {card.rarity.name}")
                cards_added += 1
        
        # FASE 2B: Si aún faltan cartas, rellenar con el último tier disponible (respetando límite de SP)
        if remaining_needed > 0 and last_available_tier:
            logger.info(f"  [FILLBACK_EQUIPO] Rellenando {remaining_needed} cartas del tier {last_available_tier}")
            available = [c for c in team_by_tier[last_available_tier] if c.id not in selected_set]
            
            # Si ya tenemos 2 SP, filtrar
            if sp_count >= 2:
                available = [c for c in available if c.position != "SP"]
            
            while remaining_needed > 0 and available:
                card = random.choice(available)
                selected_team_cards.append(card)
                selected_set.add(card.id)
                if card.position == "SP":
                    sp_count += 1
                available.remove(card)
                remaining_needed -= 1
                logger.info(f"    {cards_added + 1}. {card.name} ({team_id}) - Pos: {card.position} - {card.rarity.name}")
                cards_added += 1
        
        # Validar que completamos 7 cartas
        if len(selected_team_cards) < StarterPackConfig.FAVORITE_TEAM_CARDS:
            logger.warning(f"  [WARNING] Solo se obtuvieron {len(selected_team_cards)} cartas del equipo")
        
        selected_cards.extend(selected_team_cards)
        logger.info(f"  [TOTAL_EQUIPO] {len(selected_team_cards)} cartas seleccionadas")
        
        # ========== PASO 4: Verificar posiciones cubiertas ==========
        logger.info(f"\n[PASO 4] Verificar cobertura de posiciones")
        missing_positions = PackService._get_missing_positions(selected_cards)
        cards_needed = StarterPackConfig.TOTAL_CARDS - len(selected_cards)
        
        logger.info(f"  [POSICIONES_CUBIERTAS] {len(StarterPackConfig.REQUIRED_POSITIONS) - len(missing_positions)}/{len(StarterPackConfig.REQUIRED_POSITIONS)}")
        logger.info(f"  [POSICIONES_FALTANTES] {missing_positions}")
        logger.info(f"  [CARTAS_NECESARIAS] {cards_needed} cartas para completar {StarterPackConfig.TOTAL_CARDS}")
        
        # ========== PASO 5: Obtener cartas de otros equipos ==========
        logger.info(f"\n[PASO 5] Obtener cartas de otros equipos")
        other_team_cards = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id != team_id
        ).all()
        logger.info(f"  [DISPONIBLES] {len(other_team_cards)} cartas en otros equipos")
        
        # ========== PASO 6: Seleccionar cartas de otros equipos ==========
        logger.info(f"\n[PASO 6] Seleccionar {cards_needed} cartas de otros equipos")
        logger.info(f"  [ESTRATEGIA] Cubrir TODAS las posiciones faltantes primero, luego rellenar con COMMON")
        
        other_team_selected = []
        covered_positions = set()
        
        # FASE 1: Cubrir TODAS las posiciones faltantes CON CARTAS COMMON
        logger.info(f"  [FASE 1] Cubriendo {len(missing_positions)} posiciones faltantes CON COMMON")
        for pos in missing_positions:
            # Buscar SOLO cartas COMMON de esa posición
            common_cards = [c for c in other_team_cards 
                           if c.position == pos and c.rarity.name == "COMMON" and c.id not in selected_set]
            
            if common_cards:
                card = random.choice(common_cards)
                other_team_selected.append(card)
                selected_set.add(card.id)
                covered_positions.add(pos)
                logger.info(f"    [{pos}] {card.name} ({card.team_id}) - COMMON")
            else:
                logger.warning(f"    [{pos}] NO hay cartas COMMON disponibles para esta posición")
        
        # Verificar qué posiciones NO se cubrieron
        uncovered = set(missing_positions) - covered_positions
        if uncovered:
            logger.warning(f"  [POSICIONES_NO_CUBIERTAS] {uncovered}")
        
        # FASE 2: Rellenar slots restantes SOLO CON COMMON (cualquier posición)
        if len(other_team_selected) < cards_needed:
            logger.info(f"  [FASE 2] Rellenando {cards_needed - len(other_team_selected)} slots con COMMON (sin posición específica)")
            remaining_common = [c for c in other_team_cards 
                               if c.rarity.name == "COMMON" and c.id not in selected_set]
            need_more = cards_needed - len(other_team_selected)
            
            if remaining_common:
                fillback = random.sample(remaining_common, min(need_more, len(remaining_common)))
                other_team_selected.extend(fillback)
                selected_set.update(c.id for c in fillback)
                logger.info(f"    → Agregadas {len(fillback)} cartas COMMON de relleno")
        
        selected_cards.extend(other_team_selected)
        logger.info(f"  [TOTAL_OTROS] {len(other_team_selected)} cartas de otros equipos")
        
        # ========== PASO 7: Mezclar cartas ==========
        logger.info(f"\n[PASO 7] Mezclar cartas")
        random.shuffle(selected_cards)
        
        # ========== PASO 8: Resumen final ==========
        logger.info(f"\n[PASO 8] RESUMEN FINAL")
        logger.info(f"  [TOTAL_CARTAS] {len(selected_cards)}")
        
        # Por equipo
        logger.info(f"  [POR_EQUIPO]")
        team_comp = {}
        for card in selected_cards:
            team_comp[card.team_id] = team_comp.get(card.team_id, 0) + 1
        for t in sorted(team_comp.keys()):
            logger.info(f"    - {t}: {team_comp[t]}")
        
        # Por rareza
        logger.info(f"  [POR_RAREZA]")
        rarity_comp = {}
        for card in selected_cards:
            r = card.rarity.name if card.rarity else "COMMON"
            rarity_comp[r] = rarity_comp.get(r, 0) + 1
        for r in StarterPackConfig.TIER_PRIORITY:
            if r in rarity_comp:
                logger.info(f"    - {r}: {rarity_comp[r]}")
        
        # Por posición
        logger.info(f"  [POR_POSICION]")
        pos_comp = {}
        for card in selected_cards:
            pos_comp[card.position] = pos_comp.get(card.position, 0) + 1
        for pos in sorted(pos_comp.keys()):
            logger.info(f"    - {pos}: {pos_comp[pos]}")
        
        # ========== PASO 9: Guardar en inventario ==========
        logger.info(f"\n[PASO 9] Guardar cartas en inventario")
        for i, card in enumerate(selected_cards, 1):
            existing = db.query(UserCardInventory).filter(
                UserCardInventory.user_id == user_id,
                UserCardInventory.card_id == card.id
            ).first()
            
            if not existing:
                inventory_item = UserCardInventory(user_id=user_id, card_id=card.id)
                db.add(inventory_item)
            
            logger.info(f"  {i}. {card.name} ({card.team_id}) - {card.rarity.name}")
        
        # ========== PASO 10: Actualizar estado usuario ==========
        logger.info(f"\n[PASO 10] Actualizar estado del usuario")
        user.has_completed_onboarding = True
        logger.info(f"  [UPDATE] has_completed_onboarding = True")
        
        # ========== PASO 11: Inicializar cartera ==========
        logger.info(f"\n[PASO 11] Inicializar cartera")
        wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
        if not wallet:
            wallet = UserWallet(user_id=user_id, stamps=1000)
            db.add(wallet)
            logger.info(f"  [NEW_WALLET] Creada con 1000 stamps")
        else:
            logger.info(f"  [EXISTING_WALLET] Ya existe con {wallet.stamps} stamps")
        
        # ========== Guardar cambios en BD ==========
        logger.info(f"\n[COMMIT] Guardando cambios...")
        db.commit()
        logger.info(f"[COMMIT_SUCCESS] Completado")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"[ASSIGN_STARTER_PACK] FIN - {len(selected_cards)} cartas asignadas")
        logger.info(f"{'='*80}\n")
        
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
        wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
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
            matching_cards = db.query(PlayerCardModel).filter(
                PlayerCardModel.rarity == selected_rarity
            ).all()

            if matching_cards:
                drawn_card = random.choice(matching_cards)
            else:
                # Fallback: si no hay cartas de esa rareza, tomar cualquiera
                drawn_card = db.query(PlayerCardModel).first()

            if drawn_card:
                # Guardar en inventario
                inventory_item = UserCardInventory(user_id=user_id, card_id=drawn_card.id)
                db.add(inventory_item)
                pulled_cards.append(drawn_card)

        db.commit()
        return pulled_cards

