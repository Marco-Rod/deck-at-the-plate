"""Explicita pfx_x/pfx_z y su unidad SOURCE en perfiles de pitcheo.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "pitcher_pitch_profiles",
        "avg_horizontal_break",
        new_column_name="avg_pfx_x",
        existing_type=sa.Numeric(7, 4),
        comment="Statcast pfx_x promedio, en pies",
    )
    op.alter_column(
        "pitcher_pitch_profiles",
        "avg_vertical_break",
        new_column_name="avg_pfx_z",
        existing_type=sa.Numeric(7, 4),
        comment="Statcast pfx_z promedio, en pies",
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_pfx_x",
        "pitcher_pitch_profiles",
        "avg_pfx_x >= -10 AND avg_pfx_x <= 10",
    )
    op.create_check_constraint(
        "ck_pitcher_pitch_profiles_pfx_z",
        "pitcher_pitch_profiles",
        "avg_pfx_z >= -10 AND avg_pfx_z <= 10",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pitcher_pitch_profiles_pfx_z", "pitcher_pitch_profiles", type_="check")
    op.drop_constraint("ck_pitcher_pitch_profiles_pfx_x", "pitcher_pitch_profiles", type_="check")
    op.alter_column(
        "pitcher_pitch_profiles",
        "avg_pfx_z",
        new_column_name="avg_vertical_break",
        existing_type=sa.Numeric(7, 4),
        comment=None,
    )
    op.alter_column(
        "pitcher_pitch_profiles",
        "avg_pfx_x",
        new_column_name="avg_horizontal_break",
        existing_type=sa.Numeric(7, 4),
        comment=None,
    )
