"""
Catálogo publicado de cartas (plan V2 §22-§27)
==============================================
CardCatalog: generación atómica e inmutable de cartas jugables. Un catálogo
atraviesa estados BUILDING → VALIDATING → ACTIVE (o RETIRED/FAILED) y solo
puede existir UNO ACTIVE por (season, edition_type). Las cartas publicadas
apuntan al catálogo vía player_cards.catalog_id.
"""
import uuid

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.core.time import utcnow


def _new_id() -> str:
    return str(uuid.uuid4())


class CardCatalog(Base):
    __tablename__ = "card_catalogs"
    __table_args__ = (
        UniqueConstraint(
            "season", "edition_type", "version", name="uq_card_catalogs_season_type_version"
        ),
        # Un solo catálogo ACTIVE por (season, edition_type): publicación atómica.
        Index(
            "uq_card_catalogs_active_per_season_type",
            "season",
            "edition_type",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    # Estados: BUILDING / VALIDATING / ACTIVE / RETIRED / FAILED
    STATUSES = ("BUILDING", "VALIDATING", "ACTIVE", "RETIRED", "FAILED")

    id = Column(String(36), primary_key=True, default=_new_id)
    season = Column(SmallInteger, nullable=False, index=True)
    edition_type = Column(String(50), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="BUILDING", index=True)
    rating_model_version = Column(String(30), nullable=True, index=True)
    # Corte estadístico (PlayerSeason.data_end_date) usado para los ratings.
    data_end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    cards = relationship("PlayerCardModel", back_populates="catalog")