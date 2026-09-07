"""Agrega snapshots factuales para ediciones MOMENT.

Revision ID: 0031
Revises: 0030
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0031"
down_revision: Union[str, None] = "0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SOURCE_TYPES = ("STATCAST", "MLB_STATS_API", "GAME", "EVENT", "MANUAL")


def upgrade() -> None:
    source_type = postgresql.ENUM(
        *SOURCE_TYPES, name="momentcontextsourcetype", create_type=False
    )
    source_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "moment_contexts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("card_edition_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("context_version", sa.String(length=40), nullable=False),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('BATTER', 'PITCHER')", name="ck_moment_contexts_role"
        ),
        sa.CheckConstraint(
            "season >= 1900 AND season <= 2100", name="ck_moment_contexts_season"
        ),
        sa.CheckConstraint(
            "length(trim(source_reference)) > 0",
            name="ck_moment_contexts_source_reference_nonempty",
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64", name="ck_moment_contexts_input_hash"
        ),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["card_edition_id"], ["card_editions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id",
            "card_edition_id",
            "role",
            "context_version",
            name="uq_moment_contexts_identity",
        ),
    )
    for column in (
        "player_id",
        "card_edition_id",
        "role",
        "season",
        "occurred_at",
        "source_type",
        "source_reference",
        "context_version",
        "input_hash",
    ):
        op.create_index(f"ix_moment_contexts_{column}", "moment_contexts", [column])


def downgrade() -> None:
    op.drop_table("moment_contexts")
    postgresql.ENUM(name="momentcontextsourcetype").drop(
        op.get_bind(), checkfirst=True
    )
