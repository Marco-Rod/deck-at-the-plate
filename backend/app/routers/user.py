from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import UserProfileResponseSchema, UserInventoryResponseSchema
from app.database import get_db
from app.models import User, UserWallet, UserCardInventory, PlayerCardModel

router = APIRouter(prefix="/api/v1/user", tags=["User & Inventory"])


@router.get("/{user_id}/profile", response_model=UserProfileResponseSchema)
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    """Obtiene la información general del usuario y su saldo de monedas."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
    
    # Si por alguna razón el usuario no tiene wallet creada, se inicializa con valores base
    if not wallet:
        wallet = UserWallet(user_id=user_id, stamps=1000, gems=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

    return {
        "user_id": user.id,
        "username": user.username,
        "created_at": user.created_at,
        "wallet": {
            "stamps": wallet.stamps,
            "gems": wallet.gems
        }
    }


@router.get("/{user_id}/inventory", response_model=UserInventoryResponseSchema)
def get_user_inventory(user_id: str, db: Session = Depends(get_db)):
    """Devuelve la lista completa de cartas que posee el usuario en su colección."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    inventory_items = (
        db.query(UserCardInventory)
        .filter(UserCardInventory.user_id == user_id)
        .all()
    )

    cards_list = []
    for item in inventory_items:
        card = db.query(PlayerCardModel).filter(PlayerCardModel.id == item.card_id).first()
        if card:
            cards_list.append({
                "inventory_id": item.id,
                "acquired_at": item.acquired_at,
                "card": card
            })

    return {
        "user_id": user_id,
        "total_cards": len(cards_list),
        "inventory": cards_list
    }