"""Persiste swings como denominador del whiff rate de pitcher.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pitcher_season_stats",
        sa.Column("swings", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    # Backfill conservador: aproxima el denominador desde la tasa histórica y
    # mantiene los invariantes. Un rebuild desde RAW reemplaza esta estimación.
    op.execute(
        "UPDATE pitcher_season_stats SET swings = "
        "CASE WHEN whiff_rate IS NOT NULL AND whiff_rate > 0 "
        "THEN LEAST(pitches, GREATEST(whiffs, ROUND(whiffs::numeric / whiff_rate)::integer)) "
        "ELSE whiffs END"
    )
    op.create_check_constraint(
        "ck_pitcher_season_stats_whiff_counts",
        "pitcher_season_stats",
        "swings >= 0 AND whiffs >= 0 AND whiffs <= swings",
    )
    op.create_check_constraint(
        "ck_pitcher_season_stats_swings_pitches",
        "pitcher_season_stats",
        "swings <= pitches",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pitcher_season_stats_swings_pitches", "pitcher_season_stats", type_="check")
    op.drop_constraint("ck_pitcher_season_stats_whiff_counts", "pitcher_season_stats", type_="check")
    op.drop_column("pitcher_season_stats", "swings")
