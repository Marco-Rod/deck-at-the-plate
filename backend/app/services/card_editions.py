"""Operaciones explícitas sobre ediciones de cartas."""

from sqlalchemy.orm import Session

from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
)
from etl.services.card_rating_policies import BASE_RATING_POLICY_VERSION
from etl.services.base_eligibility_policy import BASE_ELIGIBILITY_POLICY_VERSION


def ensure_system_base_edition(db: Session, *, season: int) -> CardEdition:
    """Crea/resuelve idempotentemente la edición BASE del flujo normal."""
    identity = {
        "season": season,
        "code": f"{season}_BASE",
        "version": "edition-1.0",
    }
    edition = db.query(CardEdition).filter_by(**identity).one_or_none()
    if edition is None:
        edition = CardEdition(
            **identity,
            name=f"{season} Base Set",
            edition_type=CardEditionType.BASE,
            is_active=True,
            source_type=CardEditionSourceType.SYSTEM,
            source_reference="card-catalog:base",
            rating_policy_version=BASE_RATING_POLICY_VERSION,
            eligibility_policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
            metadata_payload={"policy": "SYSTEM_BASE"},
        )
        db.add(edition)
        db.flush()
    elif (
        edition.edition_type != CardEditionType.BASE
        or edition.source_type != CardEditionSourceType.SYSTEM
    ):
        raise ValueError("la identidad BASE existente tiene provenance incompatible")
    if edition.rating_policy_version is None:
        edition.rating_policy_version = BASE_RATING_POLICY_VERSION
    return edition
