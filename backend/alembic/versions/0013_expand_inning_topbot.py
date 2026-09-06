"""Amplía inning_topbot para persistir Top/Bottom.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "raw_pitch_events",
        "inning_topbot",
        existing_type=sa.String(length=3),
        type_=sa.String(length=10),
        existing_nullable=True,
    )


def downgrade() -> None:
    # El valor canónico anterior cabía en VARCHAR(3).
    op.execute(
        "UPDATE raw_pitch_events SET inning_topbot = 'Bot' "
        "WHERE inning_topbot = 'Bottom'"
    )
    op.alter_column(
        "raw_pitch_events",
        "inning_topbot",
        existing_type=sa.String(length=10),
        type_=sa.String(length=3),
        existing_nullable=True,
    )
