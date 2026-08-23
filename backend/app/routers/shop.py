from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import StarterPackResponseSchema, OpenPackResponseSchema
from app.database import get_db
from app.services.pack_service import PackService

router = APIRouter(prefix="/api/v1/shop", tags=["Shop & Packs"])


@router.post("/starter-pack", response_model=StarterPackResponseSchema)
def claim_starter_pack(user_id: str, team_id: str, db: Session = Depends(get_db)):
    """Entrega el mazo de bienvenida (Starter Pack) al usuario."""
    cards = PackService.assign_starter_pack(db, user_id=user_id, team_id=team_id)
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