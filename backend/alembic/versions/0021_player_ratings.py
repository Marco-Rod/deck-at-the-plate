"""Agrega contrato versionado player_ratings.

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RATING_COLUMNS = (
    "contact_rating", "power_rating", "vision_rating", "clutch_rating",
    "velocity_rating", "control_rating", "movement_rating", "stuff_rating",
    "overall_rating",
)


def upgrade() -> None:
    op.create_table(
        "player_ratings",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("player_id", sa.String(36), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("rating_model_version", sa.String(40), nullable=False),
        sa.Column("distribution_version", sa.String(40), nullable=False),
        sa.Column("data_start_date", sa.Date(), nullable=False),
        sa.Column("data_end_date", sa.Date(), nullable=False),
        sa.Column("contact_rating", sa.SmallInteger(), nullable=True),
        sa.Column("power_rating", sa.SmallInteger(), nullable=True),
        sa.Column("vision_rating", sa.SmallInteger(), nullable=True),
        sa.Column("clutch_rating", sa.SmallInteger(), nullable=True),
        sa.Column("velocity_rating", sa.SmallInteger(), nullable=True),
        sa.Column("control_rating", sa.SmallInteger(), nullable=True),
        sa.Column("movement_rating", sa.SmallInteger(), nullable=True),
        sa.Column("stuff_rating", sa.SmallInteger(), nullable=True),
        sa.Column("overall_rating", sa.SmallInteger(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("season >= 1900 AND season <= 2100", name="ck_player_ratings_season"),
        sa.CheckConstraint("data_end_date >= data_start_date", name="ck_player_ratings_window"),
        sa.CheckConstraint("role IN ('BATTER', 'PITCHER')", name="ck_player_ratings_role"),
        sa.CheckConstraint("length(input_hash) = 64", name="ck_player_ratings_input_hash"),
        sa.CheckConstraint(
            "(role = 'BATTER' AND contact_rating IS NOT NULL AND power_rating IS NOT NULL "
            "AND vision_rating IS NOT NULL AND clutch_rating IS NOT NULL "
            "AND velocity_rating IS NULL AND control_rating IS NULL "
            "AND movement_rating IS NULL AND stuff_rating IS NULL) OR "
            "(role = 'PITCHER' AND velocity_rating IS NOT NULL AND control_rating IS NOT NULL "
            "AND movement_rating IS NOT NULL AND stuff_rating IS NOT NULL "
            "AND contact_rating IS NULL AND power_rating IS NULL "
            "AND vision_rating IS NULL AND clutch_rating IS NULL)",
            name="ck_player_ratings_complete_role_shape",
        ),
        *(sa.CheckConstraint(
            f"{column} IS NULL OR ({column} >= 40 AND {column} <= 99)",
            name=f"ck_player_ratings_{column}_range",
        ) for column in RATING_COLUMNS),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id", "season", "role", "rating_model_version",
            "distribution_version", "data_start_date", "data_end_date",
            name="uq_player_ratings_identity",
        ),
    )
    for column in (
        "player_id", "season", "role", "rating_model_version",
        "distribution_version", "data_end_date",
    ):
        op.create_index(f"ix_player_ratings_{column}", "player_ratings", [column])


def downgrade() -> None:
    for column in reversed((
        "player_id", "season", "role", "rating_model_version",
        "distribution_version", "data_end_date",
    )):
        op.drop_index(f"ix_player_ratings_{column}", table_name="player_ratings")
    op.drop_table("player_ratings")
