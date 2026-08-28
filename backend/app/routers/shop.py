from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.schemas import StarterPackResponseSchema, OpenPackResponseSchema
from app.database import get_db
from app.services.pack_service import PackService
from app.models import User, UserCardInventory, PlayerCardModel, UserTeam

router = APIRouter(prefix="/api/v1/shop", tags=["Shop & Packs"])
logger = logging.getLogger(__name__)


@router.post("/starter-pack", response_model=StarterPackResponseSchema)
def claim_starter_pack(user_id: str, team_id: str, db: Session = Depends(get_db)):
    """
    Entrega el mazo de bienvenida (Starter Pack) al usuario.
    Asigna 13 cartas inteligentemente:
    - 5 fielders del equipo elegido
    - 2 pitchers del equipo elegido  
    - 6 cartas random de otros equipos
    """
    logger.info(f"=== STARTER PACK REQUEST ===")
    logger.info(f"[ENDPOINT] Recibido claim_starter_pack request")
    logger.info(f"[PARAMS] user_id={user_id}, team_id={team_id}")
    logger.info(f"[PARAMS_TYPE] user_id type={type(user_id).__name__}, team_id type={type(team_id).__name__}")
    
    user_team = db.query(UserTeam).filter(UserTeam.user_id == user_id).first()
    
    # Si no ha creado un club, requerimos que cree su franquicia primero
    if not user_team:
        logger.warning(f"[ERROR] Usuario {user_id} no tiene club creado")
        raise HTTPException(status_code=400, detail="Debes fundar tu club antes de reclamar el sobre inicial")

    logger.info(f"[VALIDATION] Usuario {user_id} tiene club creado")
    
    # Usar la nueva lógica de asignación inteligente
    cards = PackService.assign_starter_pack(db, user_id=user_id, team_id=team_id)
    
    logger.info(f"[SUCCESS] Starter pack asignado: {len(cards)} cartas devueltas")
    
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