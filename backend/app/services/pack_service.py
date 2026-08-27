import random
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import PlayerCardModel, CardRarity, UserWallet, UserCardInventory, User


class PackService:
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
    def assign_starter_pack(db: Session, user_id: str, team_id: str) -> List[PlayerCardModel]:
        """
        Asigna un mazo inicial de 13 cartas optimizado con distribución de raridades:
        
        Composición:
        - 5 jugadores inf/outf del equipo elegido (diversificando posiciones)
        - 2 lanzadores del equipo elegido
        - 6 jugadores aleatorios de otros equipos (cubriendo posiciones faltantes)
        
        Total: 13 cartas (9 fielders + 4 pitchers)
        
        Distribución de raridades:
        - 2 SILVER (mejor calidad)
        - 4 BRONZE 
        - 7 COMMON (mayoría)
        
        Garantiza cobertura de todas las posiciones del campo necesarias para un lineup.
        """
        team_id = team_id.upper()
        
        selected_cards = []
        
        # Posiciones requeridas para un lineup: P, C, 1B, 2B, 3B, SS, LF, CF, RF
        REQUIRED_POSITIONS = {"P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"}
        PITCHER_POSITIONS = {"SP", "RP", "CP"}
        
        # Distribución de raridades deseada para el pack
        RARITY_DISTRIBUTION = {
            "SILVER": 2,
            "BRONZE": 4,
            "COMMON": 7,
        }
        
        # 1. OBTENER JUGADORES DEL EQUIPO ELEGIDO (todos ordenados por rareza)
        team_fielders = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id == team_id,
            PlayerCardModel.position.notin_(PITCHER_POSITIONS),
            ~PlayerCardModel.is_two_way
        ).order_by(PlayerCardModel.rarity).all()
        
        team_pitchers = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id == team_id,
            PlayerCardModel.position.in_(PITCHER_POSITIONS)
        ).order_by(PlayerCardModel.rarity).all()
        
        # 2. SELECCIONAR 5 FIELDERS DEL EQUIPO (DIVERSIFICANDO POSICIONES)
        if len(team_fielders) >= 5:
            # Agrupar por posición
            fielders_by_pos = {}
            for card in team_fielders:
                pos = card.position
                if pos not in fielders_by_pos:
                    fielders_by_pos[pos] = []
                fielders_by_pos[pos].append(card)
            
            # Seleccionar uno de cada posición única hasta llegar a 5
            selected_from_team_fielders = []
            for pos in sorted(fielders_by_pos.keys()):
                if len(selected_from_team_fielders) < 5:
                    selected_from_team_fielders.append(random.choice(fielders_by_pos[pos]))
            
            # Si aún necesitamos más, agregar más de otras posiciones
            remaining_fielders = [c for c in team_fielders if c not in selected_from_team_fielders]
            while len(selected_from_team_fielders) < 5 and remaining_fielders:
                card = random.choice(remaining_fielders)
                selected_from_team_fielders.append(card)
                remaining_fielders.remove(card)
            
            selected_cards.extend(selected_from_team_fielders)
        else:
            selected_cards.extend(team_fielders)
        
        # 3. SELECCIONAR 2 LANZADORES DEL EQUIPO
        if len(team_pitchers) >= 2:
            selected_cards.extend(random.sample(team_pitchers, 2))
        else:
            selected_cards.extend(team_pitchers)
        
        # 4. OBTENER JUGADORES DE OTROS EQUIPOS (PARA COMPLETAR 6 MÁS)
        # Primero, verificar qué posiciones ya están cubiertas
        covered_positions = {}
        for card in selected_cards:
            pos = card.position
            covered_positions[pos] = covered_positions.get(pos, 0) + 1
        
        # Identificar posiciones de campo que faltan
        missing_positions = []
        for pos in REQUIRED_POSITIONS:
            if pos == "P":
                continue  # P es lanzador, ya manejado
            if covered_positions.get(pos, 0) == 0:
                missing_positions.append(pos)
        
        cards_needed = 13 - len(selected_cards)  # Normalmente 6
        
        # Obtener todas las cartas de otros equipos
        other_team_cards = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id != team_id
        ).all()
        
        # Separar cartas por equipo para dar prioridad al equipo favorito del usuario
        # Si el usuario tiene un equipo favorito diferente al elegido, darlo prioridad
        user = db.query(User).filter(User.id == user_id).first()
        favorite_team_id = user.favorite_team_id if user else None
        
        # Dividir cartas: equipo favorito vs otros
        favorite_team_cards = []
        other_cards = []
        
        if favorite_team_id and favorite_team_id != team_id:
            for card in other_team_cards:
                if card.team_id == favorite_team_id:
                    favorite_team_cards.append(card)
                else:
                    other_cards.append(card)
        else:
            # Si no hay equipo favorito o es el mismo, todas van a "otros"
            other_cards = other_team_cards
        
        # Agrupar cartas por rareza (priorizando equipo favorito)
        favorite_by_rarity = {}
        other_by_rarity = {}
        
        for card in favorite_team_cards:
            rarity = card.rarity.value if card.rarity else "COMMON"
            if rarity not in favorite_by_rarity:
                favorite_by_rarity[rarity] = []
            favorite_by_rarity[rarity].append(card)
        
        for card in other_cards:
            rarity = card.rarity.value if card.rarity else "COMMON"
            if rarity not in other_by_rarity:
                other_by_rarity[rarity] = []
            other_by_rarity[rarity].append(card)
        
        other_team_selected = []
        selected_set = set()  # Tracking de cartas ya seleccionadas
        rarity_count = {}
        
        # FASE 1: Seleccionar por rareza DESEADA (SILVER → BRONZE → COMMON)
        # Priorizar equipo favorito del usuario
        rarity_priority = ["SILVER", "BRONZE", "COMMON"]
        
        for rarity in rarity_priority:
            target_count = RARITY_DISTRIBUTION.get(rarity, 0)
            if target_count == 0:
                continue
            
            cards_added_for_rarity = 0
            
            # Primero intentar con cartas del equipo favorito
            if favorite_team_id and favorite_team_id != team_id:
                favorite_available = [c for c in favorite_by_rarity.get(rarity, []) if c.id not in selected_set]
                
                # Llenar posiciones faltantes primero
                for pos in missing_positions:
                    if cards_added_for_rarity >= target_count or len(other_team_selected) >= cards_needed:
                        break
                    
                    matching = [c for c in favorite_available if c.position == pos and c.id not in selected_set]
                    if matching:
                        card = random.choice(matching)
                        other_team_selected.append(card)
                        selected_set.add(card.id)
                        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
                        cards_added_for_rarity += 1
                
                # Rellenar cuota con otras posiciones del equipo favorito
                while cards_added_for_rarity < target_count and len(other_team_selected) < cards_needed:
                    favorite_available = [c for c in favorite_by_rarity.get(rarity, []) if c.id not in selected_set]
                    if not favorite_available:
                        break
                    card = random.choice(favorite_available)
                    other_team_selected.append(card)
                    selected_set.add(card.id)
                    rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
                    cards_added_for_rarity += 1
            
            # Luego intentar con otros equipos si aún falta
            if cards_added_for_rarity < target_count and len(other_team_selected) < cards_needed:
                other_available = [c for c in other_by_rarity.get(rarity, []) if c.id not in selected_set]
                
                # Llenar posiciones faltantes primero
                for pos in missing_positions:
                    if cards_added_for_rarity >= target_count or len(other_team_selected) >= cards_needed:
                        break
                    
                    matching = [c for c in other_available if c.position == pos and c.id not in selected_set]
                    if matching:
                        card = random.choice(matching)
                        other_team_selected.append(card)
                        selected_set.add(card.id)
                        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
                        cards_added_for_rarity += 1
                
                # Rellenar cuota con otras posiciones
                while cards_added_for_rarity < target_count and len(other_team_selected) < cards_needed:
                    other_available = [c for c in other_by_rarity.get(rarity, []) if c.id not in selected_set]
                    if not other_available:
                        break
                    card = random.choice(other_available)
                    other_team_selected.append(card)
                    selected_set.add(card.id)
                    rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
                    cards_added_for_rarity += 1
        
        # FASE 2: Si aún faltan cartas, llenar con cualquiera (sin importar rareza)
        if len(other_team_selected) < cards_needed:
            # Primero intentar con equipo favorito
            if favorite_team_id and favorite_team_id != team_id:
                remaining = [c for c in favorite_team_cards if c.id not in selected_set]
                while len(other_team_selected) < cards_needed and remaining:
                    card = random.choice(remaining)
                    other_team_selected.append(card)
                    selected_set.add(card.id)
                    card_rarity = card.rarity.value if card.rarity else "COMMON"
                    rarity_count[card_rarity] = rarity_count.get(card_rarity, 0) + 1
                    remaining.remove(card)
            
            # Luego con otros equipos
            if len(other_team_selected) < cards_needed:
                remaining = [c for c in other_cards if c.id not in selected_set]
                while len(other_team_selected) < cards_needed and remaining:
                    card = random.choice(remaining)
                    other_team_selected.append(card)
                    selected_set.add(card.id)
                    card_rarity = card.rarity.value if card.rarity else "COMMON"
                    rarity_count[card_rarity] = rarity_count.get(card_rarity, 0) + 1
                    remaining.remove(card)
        
        selected_cards.extend(other_team_selected)
        
        if len(selected_cards) < 13:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Catálogo insuficiente en DB. Se requieren 13 cartas únicas y solo se obtuvieron {len(selected_cards)}."
            )
        
        # 5. Mezclar las cartas aleatoriamente para sorpresa
        random.shuffle(selected_cards)

        # 6. Guardar en el inventario del usuario evitando duplicados
        assigned_items = []
        for card in selected_cards:
            already_exists = db.query(UserCardInventory).filter(
                UserCardInventory.user_id == user_id,
                UserCardInventory.card_id == card.id
            ).first()

            if not already_exists:
                inventory_item = UserCardInventory(user_id=user_id, card_id=card.id)
                db.add(inventory_item)

            assigned_items.append(card)

        # 7. Marcar onboarding completo y establecer equipo favorito
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.favorite_team_id = team_id
            user.has_completed_onboarding = True

        # 8. Inicializar cartera con 1000 Stamps
        wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
        if not wallet:
            wallet = UserWallet(user_id=user_id, stamps=1000)
            db.add(wallet)

        db.commit()
        return assigned_items

    @classmethod
    def open_pack(cls, db: Session, user_id: str, pack_type: str) -> List[PlayerCardModel]:
        """Verifica saldo de stamps, cobra el sobre y genera las cartas obtenidas."""
        pack_type = pack_type.upper()
        if pack_type not in cls.PACK_RATES:
            raise HTTPException(status_code=400, detail="Tipo de sobre no válido")

        pack_info = cls.PACK_RATES[pack_type]

        # 1. Verificar Cartera
        wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
        if not wallet or wallet.stamps < pack_info["price"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Stamps insuficientes. Requieres {pack_info['price']} stamps."
            )

        # 2. Deducir costo
        wallet.stamps -= pack_info["price"]

        # 3. Calcular Cartas por Probabilidad
        pulled_cards = []
        rarities = list(pack_info["rates"].keys())
        probabilities = list(pack_info["rates"].values())

        for _ in range(pack_info["cards_count"]):
            # Selección de rareza ponderada
            selected_rarity = random.choices(rarities, weights=probabilities, k=1)[0]

            # Buscar cartas disponibles en DB con esa rareza
            matching_cards = db.query(PlayerCardModel).filter(PlayerCardModel.rarity == selected_rarity).all()

            if matching_cards:
                drawn_card = random.choice(matching_cards)
            else:
                # Fallback en caso de que no existan cartas de esa rareza
                drawn_card = db.query(PlayerCardModel).first()

            if drawn_card:
                # Guardar en inventario del usuario
                inventory_item = UserCardInventory(user_id=user_id, card_id=drawn_card.id)
                db.add(inventory_item)
                pulled_cards.append(drawn_card)

        db.commit()
        return pulled_cards
