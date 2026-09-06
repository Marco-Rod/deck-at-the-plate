"""Agrega Stuff nullable al perfil de generación de cartas.

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "card_generation_profiles",
        sa.Column("stuff_rating", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_card_generation_stuff",
        "card_generation_profiles",
        "stuff_rating IS NULL OR (stuff_rating >= 0 AND stuff_rating <= 99)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_card_generation_stuff", "card_generation_profiles", type_="check")
    op.drop_column("card_generation_profiles", "stuff_rating")
