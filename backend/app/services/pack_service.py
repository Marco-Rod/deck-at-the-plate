import random
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import PlayerCardModel, CardRarity, UserWallet, UserCardInventory


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
        """Asigna un mazo inicial garantizado al usuario al registrarse o crear su club."""
        team_id = team_id.upper()
        team_cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team_id).all()

        if not team_cards:
            # Si no hay cartas de ese equipo, asignamos las primeras disponibles
            team_cards = db.query(PlayerCardModel).all()

        # Seleccionamos hasta 10 cartas base para el inventario del usuario
        selected_cards = team_cards[:10] if len(team_cards) >= 10 else team_cards

        assigned_items = []
        for card in selected_cards:
            inventory_item = UserCardInventory(user_id=user_id, card_id=card.id)
            db.add(inventory_item)
            assigned_items.append(card)

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