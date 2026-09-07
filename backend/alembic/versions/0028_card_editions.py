"""Agrega el dominio versionado CardEdition.

Revision ID: 0028
Revises: 0027
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EDITION_TYPES = (
    "BASE",
    "TEAM_STAR",
    "HOT_STREAK",
    "MOMENT",
    "ALL_STAR",
    "MILESTONE",
    "AWARD",
    "POSTSEASON",
)
SOURCE_TYPES = ("SYSTEM", "GAME", "EVENT", "MANUAL")


def upgrade() -> None:
    edition_type = postgresql.ENUM(
        *EDITION_TYPES, name="cardeditiontype", create_type=False
    )
    source_type = postgresql.ENUM(
        *SOURCE_TYPES, name="cardeditionsourcetype", create_type=False
    )
    edition_type.create(op.get_bind(), checkfirst=True)
    source_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "card_editions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("edition_type", edition_type, nullable=False),
        sa.Column("season", sa.SmallInteger(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "season >= 1900 AND season <= 2100",
            name="ck_card_editions_season",
        ),
        sa.CheckConstraint(
            "length(trim(code)) > 0",
            name="ck_card_editions_code_nonempty",
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_card_editions_name_nonempty",
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at",
            name="ck_card_editions_window",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "season",
            "code",
            "version",
            name="uq_card_editions_season_code_version",
        ),
    )
    for column in (
        "code",
        "edition_type",
        "season",
        "version",
        "is_active",
        "source_type",
        "source_reference",
        "starts_at",
        "ends_at",
    ):
        op.create_index(f"ix_card_editions_{column}", "card_editions", [column])
    op.create_index(
        "ix_card_editions_type_active",
        "card_editions",
        ["edition_type", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_card_editions_type_active", table_name="card_editions")
    for column in reversed((
        "code",
        "edition_type",
        "season",
        "version",
        "is_active",
        "source_type",
        "source_reference",
        "starts_at",
        "ends_at",
    )):
        op.drop_index(f"ix_card_editions_{column}", table_name="card_editions")
    op.drop_table("card_editions")
    postgresql.ENUM(name="cardeditionsourcetype").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="cardeditiontype").drop(op.get_bind(), checkfirst=True)
