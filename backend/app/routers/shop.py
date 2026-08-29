from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.schemas import StarterPackResponseSchema, OpenPackResponseSchema
from app.database import get_db
from app.services.pack_service import PackService
from app.repositories import get_user_by_id, get_user_team
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/shop", tags=["Shop & Packs"])
logger = logging.getLogger(__name__)


@router.post("/starter-pack", response_model=StarterPackResponseSchema)
def claim_starter_pack(
    team_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """
    Entrega el mazo de bienvenida (Starter Pack) al usuario autenticado.
    Asigna 13 cartas inteligentemente:
    - 5 fielders del equipo elegido
    - 2 pitchers del equipo elegido
    - 6 cartas random de otros equipos

    Solo puede reclamarse una vez por cuenta.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Impedir reclamar el starter pack más de una vez (evita duplicados masivos).
    if user.has_completed_onboarding:
        raise HTTPException(
            status_code=400,
            detail="Ya has reclamado tu sobre inicial anteriormente.",
        )

    user_team = get_user_team(db, user_id)

    # Si no ha creado un club, requerimos que cree su franquicia primero
    if not user_team:
        logger.warning(f"[ERROR] Usuario {user_id} no tiene club creado")
        raise HTTPException(status_code=400, detail="Debes fundar tu club antes de reclamar el sobre inicial")

    # El sobre debe corresponder a la franquicia base del club del usuario.
    if user_team.base_franchise and team_id.upper() != user_team.base_franchise.upper():
        raise HTTPException(
            status_code=400,
            detail=f"El sobre debe corresponder a tu franquicia base ({user_team.base_franchise}).",
        )

    logger.info(f"[VALIDATION] Usuario {user_id} tiene club creado con franquicia {user_team.base_franchise}")

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
def open_pack(
    pack_type: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Compra y abre un sobre (BRONZE, GOLD, DIAMOND) descontando stamps de la cuenta autenticada."""
    pulled_cards = PackService.open_pack(db, user_id=user_id, pack_type=pack_type)
    return {
        "message": f"¡Sobre {pack_type.upper()} abierto con éxito!",
        "user_id": user_id,
        "cards_drawn": len(pulled_cards),
        "cards": pulled_cards
    }