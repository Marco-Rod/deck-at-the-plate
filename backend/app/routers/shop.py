from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import StarterPackResponseSchema, OpenPackResponseSchema
from app.database import get_db
from app.services.pack_service import PackService
from app.models import User, UserCardInventory, PlayerCardModel, UserTeam

router = APIRouter(prefix="/api/v1/shop", tags=["Shop & Packs"])


@router.post("/starter-pack", response_model=StarterPackResponseSchema)
def claim_starter_pack(user_id: str, team_id: str, db: Session = Depends(get_db)):
    """Entrega el mazo de bienvenida (Starter Pack) al usuario."""
    """Asigna las 25 cartas iniciales del sobre al club creado por el usuario."""
    user_team = db.query(UserTeam).filter(UserTeam.user_id == user_id).first()
    
    # Si no ha creado un club, requerimos que cree su franquicia primero
    if not user_team:
        raise HTTPException(status_code=400, detail="Debes fundar tu club antes de reclamar el sobre inicial")

    # Usamos la franquicia base asociada al club (LAD, NYY, etc.)
    franchise = user_team.base_franchise

    # Asignación de las 25 cartas (Pitchers y Bateadores) al inventario del usuario
    cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == franchise).all()
    if not cards:
        # Fallback si no hay cartas filtradas por franquicia
        cards = db.query(PlayerCardModel).limit(25).all()
    for card in cards:
        inventory_item = UserCardInventory(
            user_id=user_id,
            card_id=card.id
        )
        db.add(inventory_item)

    db.commit()
            
    return {
        "message": "Starter pack asignado exitosamente",
        "user_id": user_id,
        "cards_claimed": len(cards),
        "cards": cards
    }


@router.post("/open-pack", response_model=OpenPackResponseSchema)
def open_pack(user_id: str, pack_type: str, db: Session = Depends(get_db)):
    """Compra y abre un sobre (BRONZE, GOLD, DIAMOND) descontando stamps de la cuenta."""
    pulled_cards = PackService.open_pack(db, user_id=user_id, pack_type=pack_type)
    return {
        "message": f"¡Sobre {pack_type.upper()} abierto con éxito!",
        "user_id": user_id,
        "cards_drawn": len(pulled_cards),
        "cards": pulled_cards
    }