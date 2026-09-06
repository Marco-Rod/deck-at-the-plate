"""Conserva el histograma discreto para percentiles tie-aware de rarity.

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rating_distributions",
        sa.Column(
            "population_histogram",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.alter_column("rating_distributions", "population_histogram", server_default=None)


def downgrade() -> None:
    op.drop_column("rating_distributions", "population_histogram")
