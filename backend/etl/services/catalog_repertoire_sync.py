"""Actualización incremental del repertorio de un catálogo candidato.

No reconstruye metadata, RawPitchEvent, analytics ni ratings. Sólo copia el
``repertoire_payload`` ya calculado de los perfiles de generación hacia las
cartas de un catálogo ``VALIDATING``. Mantenerlo fuera del lifecycle protege la
inmutabilidad de catálogos ACTIVE e históricos.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.enums import PITCHER_POSITIONS
from app.models import CardCatalog, CardGenerationProfile, PlayerCardModel
from etl.services.ratings2_card_profiles import generate_card_profile_from_ratings2


@dataclass(frozen=True)
class CatalogRepertoireSyncResult:
    catalog_id: str
    inspected: int
    updated: int
    missing: int
    profiles_refreshed: int


def sync_candidate_repertoires(
    db: Session, *, catalog_id: str
) -> CatalogRepertoireSyncResult:
    """Regenera perfiles de pitchers y sincroniza sus repertorios al candidato.

    Regenerar el perfil es necesario para candidatos construidos con una
    versión anterior que aún guardaba ``repertoire_payload=None``. Es un
    refresh incremental: usa los PlayerRatings y PitcherPitchProfile ya
    persistidos, sin tocar fuentes externas ni analytics.
    """
    catalog = db.get(CardCatalog, catalog_id)
    if catalog is None:
        raise ValueError(f"CardCatalog inexistente: {catalog_id}")
    if catalog.status != "VALIDATING":
        raise ValueError(
            f"catálogo {catalog_id} está en {catalog.status}; "
            "solo un VALIDATING admite sincronización incremental"
        )

    rows = (
        db.query(PlayerCardModel, CardGenerationProfile)
        .join(
            CardGenerationProfile,
            PlayerCardModel.generation_profile_id == CardGenerationProfile.id,
        )
        .filter(PlayerCardModel.catalog_id == catalog.id)
        .all()
    )
    inspected = updated = missing = profiles_refreshed = 0
    for card, profile in rows:
        is_pitcher = card.position in PITCHER_POSITIONS or card.is_two_way
        if not is_pitcher:
            continue
        inspected += 1
        generated = generate_card_profile_from_ratings2(
            db, player_ratings_id=profile.player_ratings_id
        )
        profiles_refreshed += 1
        if generated.card_generation_profile_id is None:
            missing += 1
            continue
        profile = db.get(CardGenerationProfile, generated.card_generation_profile_id)
        expected = profile.repertoire_payload or []
        if not expected:
            missing += 1
            continue
        if card.repertoire != expected:
            card.repertoire = expected
            updated += 1
    db.commit()
    return CatalogRepertoireSyncResult(
        catalog_id=catalog.id,
        inspected=inspected,
        updated=updated,
        missing=missing,
        profiles_refreshed=profiles_refreshed,
    )
