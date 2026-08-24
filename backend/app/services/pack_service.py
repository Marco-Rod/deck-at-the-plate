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

    import random
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import PlayerCardModel, CardRarity, UserWallet, UserCardInventory


class PackService:
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
        Asigna un mazo inicial garantizado de 25 cartas ÚNICAS (sin repetir jugadores).
        Prioriza el equipo seleccionado y completa con el resto del catálogo.
        """
        team_id = team_id.upper()
        
        # 1. Obtener cartas del equipo elegido
        team_cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team_id).all()

        # 2. Obtener cartas de otros equipos
        other_cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id != team_id).all()

        # Unimos sin duplicados: primero el equipo elegido, luego otros equipos
        all_unique_cards = team_cards + other_cards
        
        if len(all_unique_cards) < 25:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Catálogo insuficiente en DB. Se requieren al menos 25 cartas únicas y hay {len(all_unique_cards)}."
            )

        # Tomamos exactamente las primeras 25 cartas únicas
        selected_cards = all_unique_cards[:25]

        # 3. Guardar en el inventario del usuario evitando duplicados de DB
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

        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.favorite_team_id = team_id
            user.has_completed_onboarding = True

        # 4. Inicializar cartera con 1000 Stamps
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