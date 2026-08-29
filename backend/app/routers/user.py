from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import UserProfileResponseSchema, UserInventoryResponseSchema, CreateTeamRequestSchema, UserTeamResponseSchema
from app.database import get_db
from app.core.enums import PITCHER_POSITIONS
from app.models import UserLineup, UserTeam
from app.repositories import (
    find_user_inventory_cards,
    get_active_lineup,
    get_card_by_id,
    get_or_create_wallet,
    get_user_by_id,
    get_user_team,
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/user", tags=["User & Inventory"])


def _get_current_user_or_404(user_id: str, db: Session):
    """Resuelve el usuario autenticado o lanza 404."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.get("/me/profile", response_model=UserProfileResponseSchema)
def get_user_profile(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """Obtiene la información general del usuario autenticado y su saldo de monedas."""
    user = _get_current_user_or_404(current_user_id, db)

    wallet = get_or_create_wallet(db, current_user_id)

    return {
        "user_id": user.id,
        "username": user.username,
        "created_at": user.created_at,
        "wallet": {
            "stamps": wallet.stamps,
            "gems": wallet.gems
        }
    }


@router.get("/me/inventory", response_model=UserInventoryResponseSchema)
def get_user_inventory(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """Devuelve la lista completa de cartas del usuario autenticado en su colección."""
    _get_current_user_or_404(current_user_id, db)

    inventory_items = find_user_inventory_cards(db, current_user_id)

    cards_list = []
    for item in inventory_items:
        card = get_card_by_id(db, item.card_id)
        if card:
            cards_list.append({
                "inventory_id": item.id,
                "acquired_at": item.acquired_at,
                "card": card
            })

    return {
        "user_id": current_user_id,
        "total_cards": len(cards_list),
        "inventory": cards_list
    }


@router.get("/me/lineup")
def get_user_active_lineup(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """Recupera la alineación activa del usuario autenticado desde la base de datos."""
    lineup = get_active_lineup(db, current_user_id)
    if not lineup:
        return {"user_id": current_user_id, "name": "Lineup Principal", "slots": {}}
    return lineup


@router.put("/me/lineup")
def save_user_lineup(
    payload: dict,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """Crea o actualiza el lineup activo del usuario autenticado en PostgreSQL."""
    _get_current_user_or_404(current_user_id, db)

    lineup = get_active_lineup(db, current_user_id)

    if not lineup:
        lineup = UserLineup(
            user_id=current_user_id,
            name=payload.get("name", "Lineup Principal"),
            is_active=True,
            slots=payload.get("slots", {})
        )
        db.add(lineup)
    else:
        lineup.slots = payload.get("slots", {})

    db.commit()
    db.refresh(lineup)
    return lineup


@router.post("/me/team", response_model=UserTeamResponseSchema)
def create_user_team(
    payload: CreateTeamRequestSchema,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """Crea el club personalizado para el usuario autenticado."""
    _get_current_user_or_404(current_user_id, db)

    existing_team = get_user_team(db, current_user_id)
    if existing_team:
        raise HTTPException(status_code=400, detail="El usuario ya tiene un club registrado")

    new_team = UserTeam(
        user_id=current_user_id,
        name=payload.name,
        short_name=payload.short_name.upper(),
        city=payload.city,
        stadium_name=payload.stadium_name,
        primary_color=payload.primary_color,
        secondary_color=payload.secondary_color,
        logo_id=payload.logo_id,
        base_franchise=payload.base_franchise
    )
    db.add(new_team)
    db.commit()
    db.refresh(new_team)
    return new_team

@router.get("/me/team", response_model=UserTeamResponseSchema)
def get_user_team(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """Obtiene los datos del club personalizado del usuario autenticado."""
    team = get_user_team(db, current_user_id)
    if not team:
        raise HTTPException(status_code=404, detail="El usuario no ha fundado ningún club")
    return team


@router.get("/me/team-stats")
def get_user_team_stats(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Calcula dinámicamente el OVR General, Bateo (BAT) y Pitcheo (PIT)
    basado en las cartas de la alineación activa guardada en la BD.
    """
    lineup = get_active_lineup(db, current_user_id)

    if not lineup or not lineup.slots:
        return {"overall": 70, "batOvr": 70, "pitOvr": 70}

    batters_ovr = []
    pitchers_ovr = []

    # Iterar sobre las posiciones asignadas en el diamante
    for slot_pos, card in lineup.slots.items():
        if not card or not isinstance(card, dict):
            continue

        ovr = card.get("overall", 70)
        pos = card.get("position", "")

        if pos in PITCHER_POSITIONS or slot_pos == "P":
            pitchers_ovr.append(ovr)
        else:
            batters_ovr.append(ovr)

    bat_ovr = round(sum(batters_ovr) / len(batters_ovr)) if batters_ovr else 70
    pit_ovr = round(sum(pitchers_ovr) / len(pitchers_ovr)) if pitchers_ovr else 70
    overall = round((bat_ovr + pit_ovr) / 2)

    return {
        "overall": overall,
        "batOvr": bat_ovr,
        "pitOvr": pit_ovr
    }