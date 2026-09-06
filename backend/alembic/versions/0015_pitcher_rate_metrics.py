"""Añade numeradores, denominadores y tasas de pitcher para Analytics.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COUNT_COLUMNS = (
    "zone_pitches",
    "zone_opportunities",
    "first_pitch_strikes",
    "first_pitch_opportunities",
    "hit_by_pitches",
    "hbp_opportunities",
    "walk_opportunities",
    "strikeout_opportunities",
    "called_strikes",
    "whiffs",
    "csw",
    "csw_opportunities",
)

RATE_COLUMNS = (
    "zone_rate",
    "first_pitch_strike_rate",
    "hbp_rate",
    "walk_rate",
    "strikeout_rate",
    "csw_rate",
)

CHECKS = (
    ("ck_pitcher_season_stats_zone_rate", "zone_rate >= 0 AND zone_rate <= 1"),
    ("ck_pitcher_season_stats_zone_counts", "zone_pitches <= zone_opportunities"),
    ("ck_pitcher_season_stats_first_pitch_strike_rate", "first_pitch_strike_rate >= 0 AND first_pitch_strike_rate <= 1"),
    ("ck_pitcher_season_stats_first_pitch_counts", "first_pitch_strikes <= first_pitch_opportunities"),
    ("ck_pitcher_season_stats_hbp_rate", "hbp_rate >= 0 AND hbp_rate <= 1"),
    ("ck_pitcher_season_stats_hbp_counts", "hit_by_pitches <= hbp_opportunities"),
    ("ck_pitcher_season_stats_walk_rate", "walk_rate >= 0 AND walk_rate <= 1"),
    ("ck_pitcher_season_stats_walk_denom", "walk_opportunities = batters_faced"),
    ("ck_pitcher_season_stats_strikeout_rate", "strikeout_rate >= 0 AND strikeout_rate <= 1"),
    ("ck_pitcher_season_stats_strikeout_denom", "strikeout_opportunities = batters_faced"),
    ("ck_pitcher_season_stats_hbp_denom", "hbp_opportunities = batters_faced"),
    ("ck_pitcher_season_stats_csw_rate", "csw_rate >= 0 AND csw_rate <= 1"),
    ("ck_pitcher_season_stats_csw_numerator", "csw = called_strikes + whiffs"),
    ("ck_pitcher_season_stats_csw_denom", "csw_opportunities = pitches"),
    ("ck_pitcher_season_stats_zone_non_negative", "zone_pitches >= 0 AND zone_opportunities >= 0"),
    ("ck_pitcher_season_stats_first_pitch_non_negative", "first_pitch_strikes >= 0 AND first_pitch_opportunities >= 0"),
    ("ck_pitcher_season_stats_hbp_non_negative", "hit_by_pitches >= 0 AND hbp_opportunities >= 0"),
    ("ck_pitcher_season_stats_walk_non_negative", "walks >= 0 AND walk_opportunities >= 0"),
    ("ck_pitcher_season_stats_strikeout_non_negative", "strikeouts >= 0 AND strikeout_opportunities >= 0"),
    ("ck_pitcher_season_stats_csw_non_negative", "called_strikes >= 0 AND whiffs >= 0 AND csw >= 0 AND csw_opportunities >= 0"),
)


def upgrade() -> None:
    for column_name in COUNT_COLUMNS:
        op.add_column(
            "pitcher_season_stats",
            sa.Column(
                column_name,
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
    for column_name in RATE_COLUMNS:
        op.add_column(
            "pitcher_season_stats",
            sa.Column(column_name, sa.Numeric(7, 6), nullable=True),
        )
    # Las filas existentes conservan los denominadores ya disponibles. Las
    # métricas que requieren volver a RAW permanecen NULL hasta el rebuild.
    op.execute(
        "UPDATE pitcher_season_stats SET "
        "hbp_opportunities = batters_faced, "
        "walk_opportunities = batters_faced, "
        "strikeout_opportunities = batters_faced, "
        "csw_opportunities = pitches, "
        "walk_rate = CASE WHEN batters_faced > 0 "
        "THEN ROUND(walks::numeric / batters_faced, 6) ELSE NULL END, "
        "strikeout_rate = CASE WHEN batters_faced > 0 "
        "THEN ROUND(strikeouts::numeric / batters_faced, 6) ELSE NULL END"
    )
    for name, condition in CHECKS:
        op.create_check_constraint(name, "pitcher_season_stats", condition)


def downgrade() -> None:
    for name, _ in reversed(CHECKS):
        op.drop_constraint(name, "pitcher_season_stats", type_="check")
    for column_name in reversed(RATE_COLUMNS):
        op.drop_column("pitcher_season_stats", column_name)
    for column_name in reversed(COUNT_COLUMNS):
        op.drop_column("pitcher_season_stats", column_name)
