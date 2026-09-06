"""Agrega numeradores y oportunidades avanzadas de batter.

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNS = (
    "chases",
    "chase_opportunities",
    "hard_hits",
    "hard_hit_opportunities",
    "barrels",
    "barrel_opportunities",
)


def upgrade() -> None:
    for column in COLUMNS:
        op.add_column(
            "batter_season_stats",
            sa.Column(column, sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("batter_season_stats", column, server_default=None)
    op.create_check_constraint(
        "ck_batter_season_stats_chase_counts",
        "batter_season_stats",
        "chases >= 0 AND chase_opportunities >= 0 AND chases <= chase_opportunities",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_chase_opportunities",
        "batter_season_stats",
        "chase_opportunities <= pitches_seen",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_hard_hit_counts",
        "batter_season_stats",
        "hard_hits >= 0 AND hard_hit_opportunities >= 0 AND hard_hits <= hard_hit_opportunities",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_hard_hit_opportunities",
        "batter_season_stats",
        "hard_hit_opportunities <= balls_in_play",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_barrel_counts",
        "batter_season_stats",
        "barrels >= 0 AND barrel_opportunities >= 0 AND barrels <= barrel_opportunities",
    )
    op.create_check_constraint(
        "ck_batter_season_stats_barrel_opportunities",
        "batter_season_stats",
        "barrel_opportunities <= balls_in_play",
    )


def downgrade() -> None:
    for constraint in (
        "ck_batter_season_stats_barrel_opportunities",
        "ck_batter_season_stats_barrel_counts",
        "ck_batter_season_stats_hard_hit_opportunities",
        "ck_batter_season_stats_hard_hit_counts",
        "ck_batter_season_stats_chase_opportunities",
        "ck_batter_season_stats_chase_counts",
    ):
        op.drop_constraint(constraint, "batter_season_stats", type_="check")
    for column in reversed(COLUMNS):
        op.drop_column("batter_season_stats", column)
