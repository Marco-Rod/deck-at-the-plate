"""Agrega 10_STRIKEOUT_GAME al enum de tipos de momento.

Revision ID: 0034
Revises: 0033
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0034"
down_revision: Union[str, None] = "0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE momenttype ADD VALUE IF NOT EXISTS '10_STRIKEOUT_GAME'")


def downgrade() -> None:
    # PostgreSQL no permite eliminar un valor individual de un enum de forma segura.
    pass
