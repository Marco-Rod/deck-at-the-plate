"""Permite NULL en atributos que no aplican al rol del perfil.

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_RATING_COLUMNS = (
    "contact_rating",
    "power_rating",
    "vision_rating",
    "clutch_rating",
    "velocity_rating",
    "control_rating",
    "movement_rating",
)


def upgrade() -> None:
    op.add_column(
        "card_generation_profiles",
        sa.Column("role", sa.String(length=10), nullable=True),
    )
    op.execute(sa.text(
        "UPDATE card_generation_profiles AS profile "
        "SET role = ratings.role "
        "FROM player_ratings AS ratings "
        "WHERE profile.player_ratings_id = ratings.id"
    ))
    op.drop_constraint(
        "uq_card_generation_profiles_season_version",
        "card_generation_profiles",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_card_generation_profiles_season_version_role",
        "card_generation_profiles",
        ["player_season_id", "rating_model_version", "role"],
    )
    op.create_check_constraint(
        "ck_card_generation_profiles_role",
        "card_generation_profiles",
        "role IS NULL OR role IN ('BATTER', 'PITCHER')",
    )
    for column in ROLE_RATING_COLUMNS:
        op.alter_column(
            "card_generation_profiles",
            column,
            existing_type=sa.SmallInteger(),
            nullable=True,
        )


def downgrade() -> None:
    assignments = ", ".join(
        f"{column} = COALESCE({column}, 0)" for column in ROLE_RATING_COLUMNS
    )
    op.execute(sa.text(f"UPDATE card_generation_profiles SET {assignments}"))
    for column in ROLE_RATING_COLUMNS:
        op.alter_column(
            "card_generation_profiles",
            column,
            existing_type=sa.SmallInteger(),
            nullable=False,
        )
    op.drop_constraint(
        "ck_card_generation_profiles_role",
        "card_generation_profiles",
        type_="check",
    )
    op.drop_constraint(
        "uq_card_generation_profiles_season_version_role",
        "card_generation_profiles",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_card_generation_profiles_season_version",
        "card_generation_profiles",
        ["player_season_id", "rating_model_version"],
    )
    op.drop_column("card_generation_profiles", "role")
