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
        Asigna un mazo inicial de 13 cartas optimizado:
        
        Composición:
        - 5 jugadores inf/outf del equipo elegido (sin duplicar posiciones)
        - 2 lanzadores del equipo elegido
        - 6 jugadores aleatorios de otros equipos (sin duplicar posiciones)
        
        Total: 13 cartas (9 fielders + 4 pitchers)
        
        Evita duplicación de posiciones para cubrir todas las posiciones del campo.
        """
        team_id = team_id.upper()
        
        selected_cards = []
        
        # 1. OBTENER JUGADORES DEL EQUIPO ELEGIDO
        team_fielders = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id == team_id,
            PlayerCardModel.position.notin_(["SP", "RP", "CP"]),
            ~PlayerCardModel.is_two_way
        ).all()
        
        team_pitchers = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id == team_id,
            PlayerCardModel.position.in_(["SP", "RP", "CP"])
        ).all()
        
        # 2. SELECCIONAR 5 FIELDERS DEL EQUIPO (SIN DUPLICAR POSICIONES)
        if len(team_fielders) >= 5:
            # Agrupar por posición
            fielders_by_pos = {}
            for card in team_fielders:
                pos = card.position
                if pos not in fielders_by_pos:
                    fielders_by_pos[pos] = []
                fielders_by_pos[pos].append(card)
            
            # Seleccionar uno de cada posición hasta llegar a 5
            selected_from_team_fielders = []
            for pos, cards in fielders_by_pos.items():
                if len(selected_from_team_fielders) < 5:
                    selected_from_team_fielders.append(random.choice(cards))
            
            # Si aún necesitamos más, agregar más de otras posiciones
            remaining_fielders = [c for c in team_fielders if c not in selected_from_team_fielders]
            while len(selected_from_team_fielders) < 5 and remaining_fielders:
                selected_from_team_fielders.append(random.choice(remaining_fielders))
                remaining_fielders.remove(selected_from_team_fielders[-1])
            
            selected_cards.extend(selected_from_team_fielders)
        else:
            selected_cards.extend(team_fielders)
        
        # 3. SELECCIONAR 2 LANZADORES DEL EQUIPO
        if len(team_pitchers) >= 2:
            selected_cards.extend(random.sample(team_pitchers, 2))
        else:
            selected_cards.extend(team_pitchers)
        
        # 4. OBTENER JUGADORES DE OTROS EQUIPOS (PARA COMPLETAR 6 MÁS)
        cards_needed = 13 - len(selected_cards)  # Normalmente 6
        
        other_team_cards = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id != team_id
        ).all()
        
        # Agrupar por posición para evitar duplicación
        other_cards_by_pos = {}
        for card in other_team_cards:
            pos = card.position
            if pos not in other_cards_by_pos:
                other_cards_by_pos[pos] = []
            other_cards_by_pos[pos].append(card)
        
        # Seleccionar cartas de otros equipos evitando duplicar posiciones ya seleccionadas
        selected_positions = {}
        for card in selected_cards:
            pos = card.position
            selected_positions[pos] = selected_positions.get(pos, 0) + 1
        
        other_team_selected = []
        for pos, cards in other_cards_by_pos.items():
            # Si esta posición ya está saturada en el pack, saltarla
            if selected_positions.get(pos, 0) >= 2:
                continue
            
            # Agregar una carta de esta posición
            if cards and len(other_team_selected) < cards_needed:
                other_team_selected.append(random.choice(cards))
                selected_positions[pos] = selected_positions.get(pos, 0) + 1
        
        # Si aún faltan cartas, agregar cualquiera (podría haber duplicación menor)
        if len(other_team_selected) < cards_needed:
            remaining = [c for c in other_team_cards if c not in other_team_selected]
            while len(other_team_selected) < cards_needed and remaining:
                card = random.choice(remaining)
                other_team_selected.append(card)
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
