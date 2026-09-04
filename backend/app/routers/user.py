from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import UserProfileResponseSchema, UserInventoryResponseSchema, CreateTeamRequestSchema, UserTeamResponseSchema, UpdateBaseFranchiseRequestSchema
from app.database import get_db
from app.models import UserLineup, UserTeam
from app.repositories import (
    find_inventory_with_cards,
    get_active_lineup,
    get_or_create_wallet,
    get_user_by_id,
    get_team_by_id,
    get_user_team as repo_get_user_team,
)
from app.services.team_ratings import compute_lineup_ratings
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
    """"Obtiene la información general del usuario autenticado y su saldo de monedas."""
    user = _get_current_user_or_404(current_user_id, db)

    wallet = get_or_create_wallet(db, current_user_id)
    db.commit()  # Persistir wallet si fue creada recién (los repos no commitean)

    return {
        "user_id": user.id,
        "username": user.username,
        "created_at": user.created_at,
        "wallet": {
            "stamps": wallet.stamps,
            "gems": wallet.gems
        },
        "has_completed_onboarding": bool(user.has_completed_onboarding)
    }


@router.get("/me/inventory", response_model=UserInventoryResponseSchema)
def get_user_inventory(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """Devuelve la lista completa de cartas del usuario autenticado en su colección."""
    _get_current_user_or_404(current_user_id, db)

    # Un solo JOIN evita el N+1 de pedir cada carta con get_card_by_id.
    inventory_rows = find_inventory_with_cards(db, current_user_id)

    cards_list = [
        {
            "inventory_id": item.id,
            "acquired_at": item.acquired_at,
            "card": card,
        }
        for item, card in inventory_rows
        if card
    ]

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

    existing_team = repo_get_user_team(db, current_user_id)
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
    team = repo_get_user_team(db, current_user_id)
    if not team:
        raise HTTPException(status_code=404, detail="El usuario no ha fundado ningún club")
    return team


@router.put("/me/team/franchise", response_model=UserTeamResponseSchema)
def update_user_team_franchise(
    payload: UpdateBaseFranchiseRequestSchema,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Fija o cambia la franquicia favorita (base_franchise) del club del usuario.

    Solo se permite elegir entre las franquicias de la liga disponibles
    (equipos is_cpu=True, es decir los 30 equipos MLB en el juego).
    """
    _get_current_user_or_404(current_user_id, db)

    team = repo_get_user_team(db, current_user_id)
    if not team:
        raise HTTPException(status_code=404, detail="El usuario no ha fundado ningún club")

    franchise_id = payload.base_franchise.upper()

    # Validar que la franquicia elegida exista en la liga (equipo is_cpu=True).
    franchise = get_team_by_id(db, franchise_id)
    if not franchise or not franchise.is_cpu:
        raise HTTPException(
            status_code=400,
            detail=f"La franquicia '{franchise_id}' no está disponible para elegir.",
        )

    team.base_franchise = franchise_id
    db.commit()
    db.refresh(team)
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

    # Los slots persistidos por team/ contienen IDs de carta. Resolverlos desde
    # el inventario autenticado antes de calcular las medias; pasar los IDs
    # directamente hacía que compute_lineup_ratings los ignorara y devolviera
    # siempre el valor por defecto.
    inventory_cards = {
        card.id: card
        for _, card in find_inventory_with_cards(db, current_user_id)
        if card
    }
    resolved_slots = {}
    for slot, stored_card in lineup.slots.items():
        card_id = stored_card.get("id") if isinstance(stored_card, dict) else stored_card
        card = inventory_cards.get(card_id)
        if card:
            resolved_slots[slot] = {
                "overall": card.overall,
                "position": card.position,
            }

    # Cálculo OVR unificado (regla única en services/team_ratings.py)
    return compute_lineup_ratings(resolved_slots, default=70)
