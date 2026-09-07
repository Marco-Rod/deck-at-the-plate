"""Resolución temporal reutilizable de snapshots oficiales de PlayerRatings."""

from datetime import date

from sqlalchemy.orm import Session

from app.models import PlayerRatings


def resolve_player_ratings_as_of(
    db: Session,
    *,
    player_id: str,
    role: str,
    season: int,
    as_of_date: date,
    rating_model_version: str,
    distribution_version: str,
) -> PlayerRatings | None:
    """Devuelve el snapshot compatible más reciente anterior al evento."""
    return (
        db.query(PlayerRatings)
        .filter(
            PlayerRatings.player_id == player_id,
            PlayerRatings.role == role,
            PlayerRatings.season == season,
            PlayerRatings.rating_model_version == rating_model_version,
            PlayerRatings.distribution_version == distribution_version,
            PlayerRatings.data_end_date < as_of_date,
        )
        .order_by(
            PlayerRatings.data_end_date.desc(),
            PlayerRatings.data_start_date.desc(),
            PlayerRatings.created_at.desc(),
        )
        .first()
    )
