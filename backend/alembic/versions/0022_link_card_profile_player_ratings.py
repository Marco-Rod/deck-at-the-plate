"""Vincula opcionalmente CardGenerationProfile con PlayerRatings.

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_player_ratings_id_model_version",
        "player_ratings",
        ["id", "rating_model_version"],
    )
    op.add_column(
        "card_generation_profiles",
        sa.Column("player_ratings_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_card_generation_profiles_player_ratings_id",
        "card_generation_profiles",
        ["player_ratings_id"],
    )
    op.create_foreign_key(
        "fk_card_generation_profiles_player_ratings_version",
        "card_generation_profiles",
        "player_ratings",
        ["player_ratings_id", "rating_model_version"],
        ["id", "rating_model_version"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_card_generation_profiles_player_ratings_version",
        "card_generation_profiles",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_card_generation_profiles_player_ratings_id",
        table_name="card_generation_profiles",
    )
    op.drop_column("card_generation_profiles", "player_ratings_id")
    op.drop_constraint("uq_player_ratings_id_model_version", "player_ratings", type_="unique")
