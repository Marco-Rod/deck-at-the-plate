"""Añade fingerprint y actualización de perfiles de carta derivados.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Los perfiles existentes quedan con NULL y se reconstruyen en el primer rerun.
    op.add_column(
        "card_generation_profiles",
        sa.Column("input_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "card_generation_profiles",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_card_generation_profiles_input_hash"),
        "card_generation_profiles",
        ["input_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_card_generation_profiles_input_hash"),
        table_name="card_generation_profiles",
    )
    op.drop_column("card_generation_profiles", "updated_at")
    op.drop_column("card_generation_profiles", "input_hash")
