"""Agrega ratings específicos por jugador, edición y rol.

Revision ID: 0030
Revises: 0029
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RATING_COLUMNS = (
    "contact_rating",
    "power_rating",
    "vision_rating",
    "clutch_rating",
    "velocity_rating",
    "control_rating",
    "movement_rating",
    "stuff_rating",
    "overall_rating",
)


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_player_ratings_id_player_role",
        "player_ratings",
        ["id", "player_id", "role"],
    )
    op.create_table(
        "card_rating_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("card_edition_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("contact_rating", sa.SmallInteger(), nullable=True),
        sa.Column("power_rating", sa.SmallInteger(), nullable=True),
        sa.Column("vision_rating", sa.SmallInteger(), nullable=True),
        sa.Column("clutch_rating", sa.SmallInteger(), nullable=True),
        sa.Column("velocity_rating", sa.SmallInteger(), nullable=True),
        sa.Column("control_rating", sa.SmallInteger(), nullable=True),
        sa.Column("movement_rating", sa.SmallInteger(), nullable=True),
        sa.Column("stuff_rating", sa.SmallInteger(), nullable=True),
        sa.Column("overall_rating", sa.SmallInteger(), nullable=False),
        sa.Column("source_player_ratings_id", sa.String(length=36), nullable=False),
        sa.Column("rating_policy_version", sa.String(length=40), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('BATTER', 'PITCHER')", name="ck_card_rating_profiles_role"
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64", name="ck_card_rating_profiles_input_hash"
        ),
        sa.CheckConstraint(
            "(role = 'BATTER' AND contact_rating IS NOT NULL "
            "AND power_rating IS NOT NULL AND vision_rating IS NOT NULL "
            "AND clutch_rating IS NOT NULL AND velocity_rating IS NULL "
            "AND control_rating IS NULL AND movement_rating IS NULL "
            "AND stuff_rating IS NULL) OR "
            "(role = 'PITCHER' AND velocity_rating IS NOT NULL "
            "AND control_rating IS NOT NULL AND movement_rating IS NOT NULL "
            "AND stuff_rating IS NOT NULL AND contact_rating IS NULL "
            "AND power_rating IS NULL AND vision_rating IS NULL "
            "AND clutch_rating IS NULL)",
            name="ck_card_rating_profiles_complete_role_shape",
        ),
        *(
            sa.CheckConstraint(
                f"{column} IS NULL OR ({column} >= 40 AND {column} <= 99)",
                name=f"ck_card_rating_profiles_{column}_range",
            )
            for column in RATING_COLUMNS
        ),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["card_edition_id"], ["card_editions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_player_ratings_id", "player_id", "role"],
            ["player_ratings.id", "player_ratings.player_id", "player_ratings.role"],
            name="fk_card_rating_profiles_source_player_role",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id",
            "card_edition_id",
            "role",
            "rating_policy_version",
            name="uq_card_rating_profiles_identity",
        ),
    )
    for column in (
        "player_id",
        "card_edition_id",
        "role",
        "source_player_ratings_id",
        "rating_policy_version",
        "input_hash",
    ):
        op.create_index(
            f"ix_card_rating_profiles_{column}", "card_rating_profiles", [column]
        )


def downgrade() -> None:
    op.drop_table("card_rating_profiles")
    op.drop_constraint(
        "uq_player_ratings_id_player_role", "player_ratings", type_="unique"
    )
